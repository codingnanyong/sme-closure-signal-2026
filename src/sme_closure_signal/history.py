"""Compare a fixed store-only model with and without official 2023 history."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from .dataset import next_quarter
from .modeling import choose_threshold, make_logistic, metrics
from .quality import KEY, canonicalize, read_csv
from .robustness import paired_area_bootstrap


def extend_store_panel(current: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    columns = KEY + ["store_count", "closure_count", "opening_count"]
    if set(current.quarter) & set(history.quarter):
        raise ValueError("과거 파일과 현재 입력의 분기가 중복됩니다.")
    table = pd.concat([history[columns], current[columns]], ignore_index=True)
    if table[KEY].isna().any().any() or table.duplicated(KEY).any():
        raise ValueError("과거 결합 입력 키의 중복·결측이 있습니다.")
    table = table.sort_values(["area_code", "industry_code", "quarter"]).reset_index(drop=True)
    groups = table.groupby(["area_code", "industry_code"], sort=False)
    following = groups.quarter.shift(-1)
    closure = groups.closure_count.shift(-1)
    available = following.eq(table.quarter.map(next_quarter)) & closure.notna()
    table["closure_next_q"] = closure.gt(0).where(available)
    for name in ["store_count", "closure_count", "opening_count"]:
        values = pd.to_numeric(table[name], errors="coerce")
        if values.lt(0).any():
            raise ValueError("점포 원천에 음수가 있습니다.")
        table[{"store_count": "log_stores", "closure_count": "log_closures", "opening_count": "log_openings"}[name]] = np.log1p(values)
    result = table.loc[available & table.store_count.ge(1)].copy()
    result["closure_next_q"] = result["closure_next_q"].astype(int)
    return result


def evaluate_history(history_path: Path, dataset: Path, output: Path) -> dict[str, object]:
    current = pd.read_csv(dataset, dtype={"quarter": str, "area_code": str, "industry_code": str}, low_memory=False)
    history = canonicalize(read_csv(history_path))
    table = extend_store_panel(current, history)
    numeric = ["log_stores", "log_closures", "log_openings"]
    valid = table.loc[table.quarter.eq("20251")].copy()
    test = table.loc[table.quarter.isin(["20252", "20253"])].copy().sort_values(KEY)
    original = current.loc[current.quarter.isin(["20252", "20253"]) & current.target_available.eq(1) & current.store_count.ge(1)].sort_values(KEY)
    if not test[KEY].reset_index(drop=True).equals(original[KEY].reset_index(drop=True)) or not np.array_equal(test.closure_next_q.astype(int), original.closure_next_q.astype(int)):
        raise ValueError("과거 자료 추가 후 평가 행·타깃이 달라졌습니다.")
    output.mkdir(parents=True, exist_ok=True)
    evaluation, choices = [], {}
    for name, earliest in [("baseline_2024", "20241"), ("history_2023_2024", "20231")]:
        train = table.loc[table.quarter.between(earliest, "20244")]
        if any(part.empty or part.closure_next_q.nunique() != 2 for part in [train, valid, test]):
            raise ValueError("기간별 표본과 두 타깃 클래스를 확인하세요.")
        model = make_logistic(numeric, 10.0)
        model.fit(train[numeric + ["industry_code"]], train.closure_next_q.astype(int))
        if model["model"].n_iter_.max() >= 1000:
            raise ValueError("과거 기간 비교 모델이 수렴하지 않았습니다.")
        valid[name] = model.predict_proba(valid[numeric + ["industry_code"]])[:, 1]
        test[name] = model.predict_proba(test[numeric + ["industry_code"]])[:, 1]
        threshold = choose_threshold(valid.closure_next_q, valid[name].to_numpy())
        choices[name] = float(average_precision_score(valid.closure_next_q, valid[name]))
        for split, part in [("validation", valid), ("test", test)]:
            evaluation.append({"experiment": name, "split": split, "training_rows": len(train), "C": 10.0,
                               **metrics(part.closure_next_q, part[name].to_numpy(), threshold)})
        print(f"fitted {name}: train={len(train)}, validation AP={choices[name]:.6f}", flush=True)
    pd.DataFrame(evaluation).to_csv(output / "evaluation.csv", index=False)
    intervals, draws = paired_area_bootstrap(test, ["history_2023_2024", "baseline_2024"], 500, 198)
    intervals.to_csv(output / "area_bootstrap_intervals.csv", index=False)
    draws.to_csv(output / "area_bootstrap_draws.csv", index=False)
    test[KEY + ["closure_next_q", "baseline_2024", "history_2023_2024"]].to_csv(output / "predictions.csv", index=False)
    metadata = {"dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
                "history_csv_sha256": hashlib.sha256(history_path.read_bytes()).hexdigest(),
                "selection_by_validation_ap": max(choices, key=choices.get), "C": 10.0, "numeric_features": numeric,
                "validation_quarters": ["20251"], "test_quarters": ["20252", "20253"], "test_rows": len(test),
                "bootstrap": {"unit": "area_code", "repeats": 500, "seed": 198, "refit": False},
                "submission_v1_changed": False,
                "limitations": ["Exploratory inspected test period", "Overlapping codes do not establish equivalent historical area definitions",
                                "Official file snapshots do not verify release-date availability", "No independent future-period test", "C fixed to prior store-only candidate"]}
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata
