import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from sme_closure_signal.modeling import features, metrics, run_benchmark, benchmark_splits


def source(quarters):
    return pd.DataFrame({"quarter": quarters, "area_code": "A", "industry_code": "I",
                         "store_count": 10, "closure_count": 1, "opening_count": 1,
                         "sales_amount": [100 * (i + 1) for i in range(len(quarters))], "sales_missing": 0})


def test_features_do_not_change_past_when_future_changes():
    frame = source(["20241", "20242", "20243", "20244", "20251"])
    before = features(frame)
    frame.loc[4, "sales_amount"] = 10**12
    after = features(frame)
    pd.testing.assert_frame_equal(before.iloc[:4], after.iloc[:4])
    assert pd.notna(before.loc[3, "sales_volatility"])


def test_sales_changes_do_not_bridge_missing_quarters():
    result = features(source(["20241", "20243", "20244", "20251"]))
    assert pd.isna(result.loc[1, "sales_change"])
    assert result["sales_volatility"].isna().all()


def test_duplicate_keys_are_rejected():
    with pytest.raises(ValueError, match="키"):
        features(source(["20241", "20241"]))


def test_benchmark_does_not_silently_train_on_added_history():
    frame = pd.DataFrame({"quarter": ["20234", "20241", "20244", "20251", "20252", "20253", "20254"]})
    train, valid, test = benchmark_splits(frame)
    assert train.quarter.tolist() == ["20241", "20244"]
    assert valid.quarter.tolist() == ["20251"]
    assert test.quarter.tolist() == ["20252", "20253"]


def test_metrics_use_frozen_threshold_and_handle_ties():
    result = metrics(pd.Series([1, 0, 1, 0, 0]), np.array([0.5] * 5), 0.6)
    assert result["recall"] == 0
    assert result["top20_rows"] == 1
    assert result["top20_precision"] == 1
    assert result["average_precision"] == pytest.approx(0.4)


def test_preview_columns_are_rejected(monkeypatch):
    monkeypatch.setattr(pd, "read_csv", lambda *a, **k: pd.DataFrame({"footfall_count": [1]}))
    with pytest.raises(ValueError, match="유동인구"):
        run_benchmark(Path("input.csv"), Path("outputs/validation/test-models"), Path("outputs/validation/test-figures"))
