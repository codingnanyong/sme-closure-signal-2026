"""Validation-only tuning, sales ablation, paired area bootstrap, and policy audit."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.metrics import f1_score, precision_score, recall_score

from .modeling import NUMERIC, choose_threshold, features, make_logistic, metrics
from .quality import KEY


class WeightedAveragePrecision:
    """Cache score order/ties; compute AP for integer cluster multiplicities."""

    def __init__(self, truth: np.ndarray, scores: np.ndarray):
        self.order = np.argsort(-np.asarray(scores), kind="stable")
        self.truth = np.asarray(truth, dtype=float)[self.order]
        sorted_scores = np.asarray(scores)[self.order]
        self.ends = np.r_[np.flatnonzero(np.diff(sorted_scores)), len(sorted_scores) - 1]

    def __call__(self, weights: np.ndarray) -> float:
        weights = np.asarray(weights)[self.order]
        tp = np.cumsum(weights * self.truth)[self.ends]
        total = np.cumsum(weights)[self.ends]
        if not len(tp) or tp[-1] == 0:
            return float("nan")
        precision = np.divide(tp, total, out=np.zeros_like(tp), where=total > 0)
        return float(np.sum(np.diff(np.r_[0.0, tp]) * precision) / tp[-1])


def paired_area_bootstrap(frame: pd.DataFrame, score_columns: list[str], repeats: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if repeats < 2:
        raise ValueError("재표집 횟수는 2 이상이어야 합니다.")
    if frame["area_code"].isna().any() or frame.empty:
        raise ValueError("상권 코드가 있는 평가 자료가 필요합니다.")
    cluster, areas = pd.factorize(frame["area_code"], sort=True)
    y = frame["closure_next_q"].to_numpy(int)
    cached = {c: WeightedAveragePrecision(y, frame[c].to_numpy()) for c in score_columns}
    rng = np.random.default_rng(seed)
    draws = []
    for iteration in range(repeats):
        # All industries and both test quarters in one area share the same weight.
        counts = rng.multinomial(len(areas), np.full(len(areas), 1 / len(areas)))
        weights = counts[cluster]
        draws.append({"iteration": iteration, **{c: ap(weights) for c, ap in cached.items()}})
    samples = pd.DataFrame(draws)
    estimates = []
    unit = np.ones(len(frame))
    for column in score_columns:
        values = samples[column].dropna()
        estimates.append({"comparison": column, "estimate": cached[column](unit),
                          "lower95": float(values.quantile(0.025)), "upper95": float(values.quantile(0.975)),
                          "valid_repeats": len(values)})
    for reference in score_columns[1:]:
        values = (samples[score_columns[0]] - samples[reference]).dropna()
        estimates.append({"comparison": f"{score_columns[0]} - {reference}",
                          "estimate": cached[score_columns[0]](unit) - cached[reference](unit),
                          "lower95": float(values.quantile(0.025)), "upper95": float(values.quantile(0.975)),
                          "valid_repeats": len(values)})
    return pd.DataFrame(estimates), samples


def select_trial(trials: list[dict[str, object]]) -> dict[str, object]:
    """Select using validation AP only, including when test metrics are present."""
    return max(trials, key=lambda row: float(row["validation_ap"]))


def run_robustness(dataset: Path, output: Path, figure_dir: Path, repeats: int = 500, seed: int = 198) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(output.resolve() / "matplotlib-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import sklearn

    raw = pd.read_csv(dataset, dtype={"quarter": str, "area_code": str, "industry_code": str}, low_memory=False)
    if any("footfall" in c.lower() for c in raw.columns):
        raise ValueError("점포·매출 전용 입력만 허용합니다.")
    table = features(raw)
    labeled = table.loc[table["target_available"].eq(1) & table["closure_next_q"].isin([0, 1]) & table["store_count"].ge(1)].copy()
    train = labeled.loc[labeled["quarter"].between("20241", "20244")]
    valid = labeled.loc[labeled["quarter"].eq("20251")].copy()
    test = labeled.loc[labeled["quarter"].isin(["20252", "20253"])].copy()
    for name, part in [("train", train), ("validation", valid), ("test", test)]:
        if part.empty or part["closure_next_q"].nunique() != 2:
            raise ValueError(f"{name} 기간과 타깃을 확인하세요.")
    families = {"full": NUMERIC, "no_sales": ["log_stores", "log_closures", "log_openings"], "exposure_industry": ["log_stores"]}
    all_trials, selected, fitted = [], {}, {}
    for family, numeric in families.items():
        family_trials = []
        candidates = {}
        for c in [0.1, 1.0, 10.0]:
            model = make_logistic(numeric, c)
            model.fit(train[numeric + ["industry_code"]], train["closure_next_q"].astype(int))
            iterations = int(model["model"].n_iter_.max())
            if iterations >= 1000:
                raise ValueError(f"수렴 실패: {family}, C={c}")
            validation_scores = model.predict_proba(valid[numeric + ["industry_code"]])[:, 1]
            trial = {"family": family, "C": c, "validation_ap": float(average_precision_score(valid["closure_next_q"], validation_scores)), "iterations": iterations}
            family_trials.append(trial)
            candidates[c] = (model, validation_scores)
            print(f"fitted {family} C={c}: validation AP={trial['validation_ap']:.6f}", flush=True)
        best = select_trial(family_trials)
        selected[family] = best
        fitted[family] = candidates[best["C"]][0]
        valid[family] = candidates[best["C"]][1]
        # Only the selected model is scored on the test; test never enters tuning.
        test[family] = fitted[family].predict_proba(test[numeric + ["industry_code"]])[:, 1]
        all_trials.extend(family_trials)
    pd.DataFrame(all_trials).to_csv(output / "tuning.csv", index=False)
    policy_model = max(selected, key=lambda family: selected[family]["validation_ap"])
    global_threshold = choose_threshold(valid["closure_next_q"], valid[policy_model].to_numpy())
    evaluation = []
    for family in families:
        threshold = choose_threshold(valid["closure_next_q"], valid[family].to_numpy())
        for split, part in [("validation", valid), ("test", test)]:
            evaluation.append({"family": family, "split": split, "C": selected[family]["C"], **metrics(part["closure_next_q"], part[family].to_numpy(), threshold)})
    pd.DataFrame(evaluation).to_csv(output / "ablation.csv", index=False)
    # Hold C fixed too, so the sales ablation is not explained by different regularization.
    fixed_c = selected["full"]["C"]
    no_sales_fixed = make_logistic(families["no_sales"], fixed_c)
    no_sales_fixed.fit(train[families["no_sales"] + ["industry_code"]], train["closure_next_q"].astype(int))
    if no_sales_fixed["model"].n_iter_.max() >= 1000:
        raise ValueError("고정 C 매출 제외 모델이 수렴하지 않았습니다.")
    test["no_sales_fixed_c"] = no_sales_fixed.predict_proba(test[families["no_sales"] + ["industry_code"]])[:, 1]
    test = test.sort_values(KEY).reset_index(drop=True)
    intervals, draws = paired_area_bootstrap(test, ["full", "no_sales", "exposure_industry", "no_sales_fixed_c"], repeats, seed)
    intervals.to_csv(output / "area_bootstrap_intervals.csv", index=False)
    draws.to_csv(output / "area_bootstrap_draws.csv", index=False)

    policies, thresholds = [], {}
    for size, validation_group in valid.groupby("size_group", observed=True):
        enough = len(validation_group) >= 100 and validation_group["closure_next_q"].sum() >= 20 and validation_group["closure_next_q"].nunique() == 2
        threshold = choose_threshold(validation_group["closure_next_q"], validation_group[policy_model].to_numpy()) if enough else global_threshold
        thresholds[str(size)] = {"threshold": threshold, "validation_rows": len(validation_group), "fallback_global": not enough}
    for size, part in test.groupby("size_group", observed=True):
        thresholds.setdefault(str(size), {"threshold": global_threshold, "validation_rows": 0, "fallback_global": True})
        for policy, threshold in [("global", global_threshold), ("size_validation_f1", thresholds[str(size)]["threshold"])]:
            row = metrics(part["closure_next_q"], part[policy_model].to_numpy(), threshold)
            policies.append({"size_group": size, "policy": policy, "predicted_positive_rows": int(part[policy_model].ge(threshold).sum()), **row})
    policy_frame = pd.DataFrame(policies)
    policy_frame.to_csv(output / "size_threshold_policies.csv", index=False)
    subgroup_rows = []
    for dimension in ["quarter", "industry_code", "size_group"]:
        for group, part in test.groupby(dimension, observed=True):
            subgroup_rows.append({"dimension": dimension, "group": group, **metrics(part["closure_next_q"], part[policy_model].to_numpy(), global_threshold)})
    groups = pd.DataFrame(subgroup_rows)
    groups.to_csv(output / "subgroups.csv", index=False)
    test["policy_score"] = test[policy_model]
    ranks = test.groupby("quarter")["policy_score"].rank(method="first", pct=True)
    test["risk_quintile"] = np.ceil(ranks * 5).clip(1, 5).astype(int)
    test["global_prediction"] = test["policy_score"].ge(global_threshold).astype(int)
    size_cutoffs = test["size_group"].map({k: v["threshold"] for k, v in thresholds.items()}).astype(float)
    test["size_threshold_prediction"] = test["policy_score"].ge(size_cutoffs).astype(int)
    test[KEY + ["store_count", "size_group", "closure_next_q"] + list(families) + ["no_sales_fixed_c", "policy_score", "risk_quintile", "global_prediction", "size_threshold_prediction"]].to_csv(output / "predictions.csv", index=False)
    quintiles = test.groupby(["quarter", "risk_quintile"])["closure_next_q"].agg(rows="size", positive_share="mean").reset_index()
    quintiles.to_csv(output / "quintiles.csv", index=False)
    summaries = []
    for policy in ["global_prediction", "size_threshold_prediction"]:
        y, predicted = test["closure_next_q"].astype(int), test[policy]
        summaries.append({"policy": policy, "rows": len(test), "predicted_positive_rows": int(predicted.sum()),
                          "true_positive_rows": int((predicted.eq(1) & y.eq(1)).sum()),
                          "precision": float(precision_score(y, predicted, zero_division=0)),
                          "recall": float(recall_score(y, predicted, zero_division=0)),
                          "f1": float(f1_score(y, predicted, zero_division=0))})
    pd.DataFrame(summaries).to_csv(output / "policy_summary.csv", index=False)

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(figure_dir / f"{name}.png", dpi=160)
        fig.savefig(figure_dir / f"{name}.svg")
        plt.close(fig)

    comparison = intervals.loc[~intervals["comparison"].str.contains(" - ")]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.errorbar(comparison["estimate"], comparison["comparison"], xerr=[comparison["estimate"] - comparison["lower95"], comparison["upper95"] - comparison["estimate"]], fmt="o", capsize=4)
    ax.set(xlabel="Average precision (95% paired area bootstrap interval)", title="Sales ablation: exploratory 2025Q2-Q3 evaluation")
    save(fig, "sales_ablation_intervals")
    fig, ax = plt.subplots(figsize=(8, 5))
    for quarter, part in quintiles.groupby("quarter"):
        ax.plot(part["risk_quintile"], part["positive_share"], marker="o", label=quarter)
    ax.set(xlabel="Risk quintile (1=low, 5=high)", ylabel="Observed next-quarter closure occurrence",
           title=f"Selected candidate: {policy_model}", xticks=[1, 2, 3, 4, 5])
    ax.legend()
    save(fig, "selected_risk_quintiles")
    sizes = ["1-5", "6-10", "11-30", "31+"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for policy in ["global", "size_validation_f1"]:
        part = policy_frame.loc[policy_frame["policy"].eq(policy)].set_index("size_group").reindex(sizes)
        for ax, metric in zip(axes, ["recall", "precision"]):
            ax.plot(sizes, part[metric], marker="o", label=policy)
            ax.set(xlabel="Store count in area-industry group", ylabel=metric, ylim=(0, 1))
            ax.legend(fontsize=8)
    fig.suptitle(f"Threshold policy diagnostic: {policy_model} (no automatic adoption)")
    save(fig, "size_threshold_tradeoff")
    industries = groups.loc[groups["dimension"].eq("industry_code")]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(industries["rows"], industries["average_precision"], alpha=0.6)
    ax.set(xscale="log", xlabel="Test rows per industry (log scale)", ylabel="Average precision", title="Industry performance and sample size (not district validation)")
    save(fig, "industry_sample_performance")
    metadata = {"dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
                "selected_trials": selected, "selected_family": policy_model, "global_threshold": global_threshold, "size_thresholds": thresholds,
                "train_quarters": sorted(train["quarter"].unique().tolist()),
                "validation_quarters": ["20251"], "test_quarters": ["20252", "20253"],
                "selection": "max_validation_AP_then_validation_F1_threshold; test never used for selection",
                "bootstrap": {"unit": "area_code; all industries and both test quarters together", "paired": True,
                              "repeats": repeats, "seed": seed, "clusters": int(test["area_code"].nunique()),
                              "interval": "percentile 95%; fixed fitted models, no refit"},
                "fixed_c_ablation": fixed_c, "sklearn_version": sklearn.__version__,
                "monotonic_quintiles": {q: bool(p["positive_share"].diff().dropna().ge(0).all()) for q, p in quintiles.groupby("quarter")},
                "limitations": ["Exploratory: test period was previously inspected", "Bootstrap conditional on fitted model and two observed quarters; no time uncertainty", "No causal sales effect or prospective policy impact", "No release-date or district validation", "Size thresholds are diagnostics requiring capacity and policy review", "Human review pending"]}
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata
