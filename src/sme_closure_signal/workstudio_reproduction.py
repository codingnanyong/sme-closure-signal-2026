"""COD-197: reproduce the Work Studio script with explicit input tables."""

def reproduce(inputs):
    import numpy as np
    import pandas as pd
    import sklearn
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, precision_recall_curve, precision_score, recall_score, f1_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    frames = [x.toPandas() if hasattr(x, 'toPandas') else x.copy() for x in inputs]
    df = pd.concat(frames, ignore_index=True)
    keys = ['quarter', 'area_code', 'industry_code']
    if df[keys].isna().any().any():
        raise ValueError("Input keys must not contain missing values")
    for c in keys:
        df[c] = df[c].astype(str)
    if df.duplicated(keys).any():
        raise ValueError("Input keys must be unique across all inputs")
    df = df.sort_values(['area_code', 'industry_code', 'quarter']).reset_index(drop=True)
    train = df[df.quarter.between('20241', '20244')].copy()
    valid = df[df.quarter.eq('20251')].copy()
    test = df[df.quarter.isin(['20252', '20253'])].copy()
    if train.empty or valid.empty:
        raise ValueError("Training and validation partitions must be nonempty")
    numeric = ['log_stores', 'log_closures', 'log_openings']
    if df[numeric + ['closure_next_q']].isna().any().any():
        raise ValueError("Model inputs must not contain missing values")
    if not df.closure_next_q.isin([0, 1]).all():
        raise ValueError("Target must be binary")
    if train.closure_next_q.nunique() != 2 or valid.closure_next_q.nunique() != 2:
        raise ValueError("Training and validation targets must contain both classes")
    transform = ColumnTransformer([
        ('numeric', Pipeline([('impute', SimpleImputer(strategy='median', add_indicator=True)), ('scale', StandardScaler())]), numeric),
        ('industry', OneHotEncoder(handle_unknown='ignore'), ['industry_code'])])
    model = Pipeline([('features', transform), ('model', LogisticRegression(C=10.0, solver='lbfgs', max_iter=1000, random_state=0))])
    model.fit(train, train.closure_next_q.astype(int))
    vscore = model.predict_proba(valid)[:, 1]
    p, r, t = precision_recall_curve(valid.closure_next_q.astype(int), vscore)
    f = 2*p[:-1]*r[:-1]/np.maximum(p[:-1]+r[:-1], 1e-15)
    threshold = float(t[int(np.argmax(f))])
    rows = []
    for name, part in [('validation', valid), ('test', test)]:
        if not len(part):
            continue
        score = model.predict_proba(part)[:, 1]
        y = part.closure_next_q.to_numpy(dtype=int)
        pred = score >= threshold
        k = int(np.ceil(len(y)*0.2))
        top = np.argsort(-score, kind='stable')[:k]
        rows.append(dict(split=name, rows=len(part), positives=int(y.sum()), average_precision=float(average_precision_score(y,score)), precision=float(precision_score(y,pred,zero_division=0)), recall=float(recall_score(y,pred,zero_division=0)), f1=float(f1_score(y,pred,zero_division=0)), top20_precision=float(y[top].mean()), top20_recall=float(y[top].sum()/y.sum()) if y.sum() else 0.0, threshold=threshold, sklearn_version=sklearn.__version__, input_count=len(inputs), C=10.0, solver='lbfgs', max_iter=1000))
    result = pd.DataFrame(rows)
    print(result.to_string(index=False))
    return result


# Work Studio injects `inputs` into the script namespace; ordinary imports do not.
if "inputs" in globals():
    result = reproduce(inputs)
