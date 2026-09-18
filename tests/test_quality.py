import pandas as pd
import pytest

import sme_closure_signal.quality as quality
from sme_closure_signal.quality import (
    canonicalize,
    continuity,
    key_coverage,
    target_summary,
    validate_sources,
)


def test_canonicalize_preserves_numeric_identifiers_with_missing_values() -> None:
    frame = pd.DataFrame(
        {
            "quarter": [20241.0, None],
            "area_code": [1001.0, None],
            "industry_code": [10.0, None],
        }
    )

    result = canonicalize(frame)

    assert result.loc[0, ["quarter", "area_code", "industry_code"]].tolist() == [
        "20241",
        "1001",
        "10",
    ]
    assert result.loc[1, ["quarter", "area_code", "industry_code"]].isna().all()


def test_key_coverage_and_continuity() -> None:
    left = pd.DataFrame({"quarter": ["20241", "20241"], "area_code": ["A", "B"]})
    right = pd.DataFrame({"quarter": ["20241", "20241"], "area_code": ["A", "C"]})
    coverage = key_coverage(left, right, ["quarter", "area_code"])
    assert coverage["matched_keys"] == 1
    assert coverage["left_match_rate"] == 0.5

    frame = pd.DataFrame(
        {"quarter": ["20241", "20241", "20242", "20242"], "area_code": ["A", "B", "A", "C"]}
    )
    result = continuity(frame, "20241", "20242")
    assert result["retained_areas"] == 1
    assert result["earlier_retention_rate"] == 0.5


def test_target_summary_reports_out_of_range_public_rate() -> None:
    stores = pd.DataFrame(
        {
            "closure_rate": [10, 150],
            "closure_count": [1, 2],
            "store_count": [10, 1],
        }
    )
    result = target_summary(stores)
    assert result["closure_rate_gt_100_rows"] == 1
    assert result["closure_count_gt_store_count_rows"] == 1


def test_validate_sources_uses_latest_common_quarter_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores = pd.DataFrame(
        {
            "quarter": ["20241", "20243", "20244"],
            "area_code": ["A", "A", "A"],
            "industry_code": ["I", "I", "I"],
            "store_count": [10, 9, 8],
            "closure_rate": [1, 2, 3],
            "closure_count": [0, 1, 1],
        }
    )
    sales = stores[["quarter", "area_code", "industry_code"]].assign(
        sales_amount=100,
        sales_count=10,
    )
    frames = iter([(stores, []), (sales, [])])
    monkeypatch.setattr(quality, "load_many", lambda _paths: next(frames))

    result = validate_sources([], [])
    latest = result["area_continuity_latest_pair"]
    assert latest is not None
    assert latest["stores"]["earlier"] == "20243"
    assert latest["stores"]["later"] == "20244"
