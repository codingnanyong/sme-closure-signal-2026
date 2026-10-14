"""Reproducible temporal benchmark using official store and sales sources only."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .dataset import next_quarter
from .quality import KEY


NUMERIC = ["log_stores", "log_closures", "log_openings", "log_sales", "sales_change", "sales_volatility"]


def make_logistic(numeric: list[str], regularization: float = 1.0) -> Pipeline:
    """Fit preprocessing only when the returned pipeline is fitted on training rows."""
    transform = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                              ("scale", StandardScaler())]), numeric),
        ("industry", OneHotEncoder(handle_unknown="ignore"), ["industry_code"]),
    ])
    return Pipeline([("features", transform), ("model", LogisticRegression(
        C=regularization, max_iter=1000, random_state=0, solver="lbfgs"))])


def features(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.copy()
    if table[KEY].isna().any().any() or table.duplicated(KEY).any():
        raise ValueError("모델 입력 키 결측·중복을 먼저 해결해야 합니다.")
    table["quarter"] = table["quarter"].astype(str)
    if not table["quarter"].str.fullmatch(r"\d{4}[1-4]").all():
        raise ValueError("분기 형식은 YYYYQ여야 합니다.")
    table = table.sort_values(["area_code", "industry_code", "quarter"]).reset_index(drop=True)
    for source, target in [("store_count", "log_stores"), ("closure_count", "log_closures"), ("opening_count", "log_openings"), ("sales_amount", "log_sales")]:
        values = pd.to_numeric(table[source], errors="coerce")
        if values.lt(0).any():
            raise ValueError(f"음수 원천값: {source}")
        table[target] = np.log1p(values)
    group = table.groupby(["area_code", "industry_code"], sort=False)
    previous_quarter = group["quarter"].shift()
    consecutive = previous_quarter.map(lambda q: next_quarter(q) if pd.notna(q) else None).eq(table["quarter"])
    # Log difference avoids division by zero and never bridges an absent quarter.
    table["sales_change"] = (table["log_sales"] - group["log_sales"].shift()).where(consecutive)
    # Three consecutive changes (four observed quarters); no future values.
    changes = table.groupby(["area_code", "industry_code"], sort=False)["sales_change"]
    table["sales_volatility"] = changes.transform(lambda s: s.rolling(3, min_periods=3).std(ddof=0))
    table["size_group"] = pd.cut(table["store_count"], [0, 5, 10, 30, np.inf], labels=["1-5", "6-10", "11-30", "31+"], right=True).astype("string")
    return table


def choose_threshold(y: pd.Series, scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y, scores)
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-15)
    return float(thresholds[int(np.argmax(f1))])


def metrics(y: pd.Series, scores: np.ndarray, threshold: float) -> dict[str, object]:
    truth = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=float)
    k = max(1, math.ceil(len(truth) * 0.2))
    order = np.argsort(-scores, kind="stable")[:k]
    positives = int(truth.sum())
    predicted = scores >= threshold
    return {"rows": len(truth), "positives": positives, "positive_share": float(truth.mean()),
            "average_precision": float(average_precision_score(truth, scores)) if positives else None,
            "precision": float(precision_score(truth, predicted, zero_division=0)),
            "recall": float(recall_score(truth, predicted, zero_division=0)),
            "f1": float(f1_score(truth, predicted, zero_division=0)),
            "top20_rows": k, "top20_precision": float(truth[order].mean()),
            "top20_recall": float(truth[order].sum() / positives) if positives else None,
            "threshold": threshold}


def run_benchmark(dataset: Path, output: Path, figures: Path) -> dict[str, object]:
    cache = output.resolve() / "matplotlib-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import sklearn

    raw = pd.read_csv(dataset, dtype={"quarter": str, "area_code": str, "industry_code": str}, low_memory=False)
    if any("footfall" in c.lower() for c in raw.columns):
        raise ValueError("점포·매출 전용 입력을 다시 생성하세요. 유동인구 컬럼은 허용하지 않습니다.")
    table = features(raw)
    eligible = table["target_available"].eq(1) & table["closure_next_q"].isin([0, 1]) & table["store_count"].ge(1)
    labeled = table.loc[eligible].copy()
    train = labeled.loc[labeled["quarter"].le("20244")]
    valid = labeled.loc[labeled["quarter"].eq("20251")]
    test = labeled.loc[labeled["quarter"].isin(["20252", "20253"])].copy()
    for name, part in [("train", train), ("validation", valid), ("test", test)]:
        if part.empty or part["closure_next_q"].nunique() != 2:
            raise ValueError(f"{name}의 기간 또는 타깃 두 클래스를 확인하세요.")
    output.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    model = make_logistic(NUMERIC)
    model.fit(train[NUMERIC + ["industry_code"]], train["closure_next_q"].astype(int))
    if model["model"].n_iter_.max() >= 1000:
        raise ValueError("로지스틱 회귀가 수렴하지 않았습니다.")
    exposure = Pipeline([
        ("features", ColumnTransformer([
            ("exposure", StandardScaler(), ["log_stores"]),
            ("industry", OneHotEncoder(handle_unknown="ignore"), ["industry_code"]),
        ])),
        ("model", LogisticRegression(C=1.0, max_iter=1000, random_state=0, solver="lbfgs")),
    ])
    exposure.fit(train[["log_stores", "industry_code"]], train["closure_next_q"].astype(int))
    if exposure["model"].n_iter_.max() >= 1000:
        raise ValueError("점포 수·업종 기준선이 수렴하지 않았습니다.")
    industry = train.groupby("industry_code")["closure_next_q"].mean()
    fallback = float(train["closure_next_q"].mean())

    def scores(part: pd.DataFrame) -> dict[str, np.ndarray]:
        # A transparent rank score; ranks depend only on the current quarter's features.
        ranks = part.groupby("quarter")[["sales_change", "sales_volatility", "log_stores"]].rank(pct=True)
        weighted = ((1 - ranks["sales_change"]).fillna(0.5) + ranks["sales_volatility"].fillna(0.5) + ranks["log_stores"].fillna(0.5)) / 3
        return {"industry_mean": part["industry_code"].map(industry).fillna(fallback).to_numpy(float),
                "current_closure": part["closure_count"].gt(0).to_numpy(float),
                "weighted_signal": weighted.to_numpy(float),
                "exposure_industry": exposure.predict_proba(part[["log_stores", "industry_code"]])[:, 1],
                "logistic": model.predict_proba(part[NUMERIC + ["industry_code"]])[:, 1]}

    val_scores, test_scores = scores(valid), scores(test)
    thresholds = {name: choose_threshold(valid["closure_next_q"], score) for name, score in val_scores.items()}
    evaluations = []
    for split, part, predictions in [("validation", valid, val_scores), ("test", test, test_scores)]:
        for name, score in predictions.items():
            evaluations.append({"split": split, "model": name, **metrics(part["closure_next_q"], score, thresholds[name])})
    evaluation = pd.DataFrame(evaluations)
    evaluation.to_csv(output / "evaluation.csv", index=False)
    quarter_evaluations = []
    for quarter in sorted(test["quarter"].unique()):
        mask = test["quarter"].eq(quarter)
        for name, score in test_scores.items():
            quarter_evaluations.append({"quarter": quarter, "model": name, **metrics(test.loc[mask, "closure_next_q"], score[mask.to_numpy()], thresholds[name])})
    pd.DataFrame(quarter_evaluations).to_csv(output / "quarter_evaluation.csv", index=False)
    # Select once on validation AP, then keep the test untouched for comparison.
    winner = max(val_scores, key=lambda name: average_precision_score(valid["closure_next_q"], val_scores[name]))
    test["score"] = test_scores[winner]
    test["prediction"] = test["score"].ge(thresholds[winner]).astype(int)
    # Deterministic ties use sorted area/industry keys; quintiles are within quarter.
    test = test.sort_values(KEY).reset_index(drop=True)
    rank = test.groupby("quarter")["score"].rank(method="first", pct=True)
    test["risk_quintile"] = np.ceil(rank * 5).clip(1, 5).astype(int)
    for name, score in test_scores.items():
        # Align original test order with the sorted export.
        original = labeled.loc[labeled["quarter"].isin(["20252", "20253"])].copy()
        original["model_score"] = score
        test[f"score_{name}"] = test[KEY].merge(original[KEY + ["model_score"]], on=KEY, validate="one_to_one")["model_score"].to_numpy()
    test[KEY + ["store_count", "closure_next_q", "score", "prediction", "risk_quintile"] + [f"score_{n}" for n in test_scores]].to_csv(output / "predictions.csv", index=False)
    slices = []
    for dimension in ["quarter", "industry_code", "size_group"]:
        for value, group in test.groupby(dimension, observed=True):
            slices.append({"dimension": dimension, "group": value, **metrics(group["closure_next_q"], group["score"].to_numpy(), thresholds[winner])})
    pd.DataFrame(slices).to_csv(output / "subgroups.csv", index=False)
    sensitivity = []
    for minimum in [1, 5, 10]:
        part = test.loc[test["store_count"].ge(minimum)]
        sensitivity.append({"min_stores": minimum, **metrics(part["closure_next_q"], part["score"].to_numpy(), thresholds[winner])})
    pd.DataFrame(sensitivity).to_csv(output / "exposure_sensitivity.csv", index=False)
    quintiles = test.groupby(["quarter", "risk_quintile"])["closure_next_q"].agg(rows="size", positive_share="mean").reset_index()
    quintiles.to_csv(output / "quintiles.csv", index=False)
    coefficients = pd.DataFrame({"feature": model["features"].get_feature_names_out(), "coefficient": model["model"].coef_[0]})
    coefficients.to_csv(output / "coefficients.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 5))
    for quarter, part in quintiles.groupby("quarter"):
        ax.plot(part["risk_quintile"], part["positive_share"], marker="o", label=quarter)
    ax.set(xlabel="Risk quintile (1=low, 5=high)", ylabel="Observed next-quarter closure occurrence", title=f"Held-out quarters: {winner}", xticks=[1, 2, 3, 4, 5])
    ax.legend(); fig.tight_layout(); fig.savefig(figures / "risk_quintiles.svg"); fig.savefig(figures / "risk_quintiles.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 5))
    comparison = evaluation.loc[evaluation["split"].eq("test")]
    ax.bar(comparison["model"], comparison["average_precision"])
    ax.set(ylabel="Average precision", title="Held-out benchmark (not business-level closure probability)")
    fig.tight_layout(); fig.savefig(figures / "model_comparison.svg"); fig.savefig(figures / "model_comparison.png", dpi=160); plt.close(fig)
    metadata = {"dataset": str(dataset), "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
                "source_scope": "official_stores_sales_only", "minimum_stores": 1,
                "rows": len(table), "excluded_unavailable_target": int(table["target_available"].ne(1).sum()),
                "excluded_nonpositive_or_missing_stores_with_target": int((table["target_available"].eq(1) & ~table["store_count"].ge(1)).sum()),
                "splits": {name: {"rows": len(part), "quarters": sorted(part["quarter"].unique().tolist())} for name, part in [("train", train), ("validation", valid), ("test", test)]},
                "selected_model": winner, "selection_rule": "maximum_validation_average_precision",
                "threshold_rule": "maximum_validation_f1", "thresholds": thresholds,
                "numeric_features": NUMERIC, "categorical_features": ["industry_code"],
                "sklearn_version": sklearn.__version__, "pandas_version": pd.__version__,
                "iterations": int(model["model"].n_iter_.max()),
                "monotonic_quintiles": {q: bool(p["positive_share"].diff().dropna().ge(0).all()) for q, p in quintiles.groupby("quarter")},
                "limitations": ["Quarter-end features assume release availability; no historical release-date backtest", "No district mapping: district validation pending", "No official footfall input", "Exposure sensitivity evaluates a fixed model, not refitted models", "AP is step-integrated average precision, not trapezoidal PR-AUC", "Top20 ties use deterministic row order", "No causal policy impact estimate", "Human review pending"]}
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata
