from pathlib import Path

import pandas as pd
import pytest

import sme_closure_signal.dataset as dataset
from sme_closure_signal.dataset import build_model_dataset, next_quarter


@pytest.mark.parametrize(
    ("value", "expected"),
    [("20241", "20242"), ("20244", "20251")],
)
def test_next_quarter(value: str, expected: str) -> None:
    assert next_quarter(value) == expected


def test_build_model_dataset_marks_only_consecutive_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    stores = pd.DataFrame(
        {
            "quarter": ["20241", "20242", "20241", "20243", "20241", "20242"],
            "area_code": ["A", "A", "B", "B", "C", "C"],
            "industry_code": ["I", "I", "I", "I", "I", "I"],
            "store_count": [10, 9, 8, 7, 6, 5],
            "closure_count": [0, 2, 0, 3, 0, None],
        }
    )
    sales = stores[["quarter", "area_code", "industry_code"]].assign(
        sales_amount=100,
        sales_count=10,
    )
    frames = iter([(stores, []), (sales, [])])
    monkeypatch.setattr(dataset, "load_many", lambda _paths: next(frames))

    result = build_model_dataset([Path("stores.csv")], [Path("sales.csv")])

    area_a = result[result["area_code"].eq("A")].reset_index(drop=True)
    assert area_a["target_available"].tolist() == [1, 0]
    assert area_a["closure_next_q"].tolist()[0] == 1
    assert pd.isna(area_a["closure_next_q"].tolist()[1])
    area_b = result[result["area_code"].eq("B")]
    assert area_b["target_available"].tolist() == [0, 0]
    area_c = result[result["area_code"].eq("C")]
    assert area_c["target_available"].tolist() == [0, 0]
    assert area_c["closure_next_q"].isna().all()
