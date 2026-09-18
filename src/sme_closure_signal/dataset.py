"""Build a quarter-area-industry model table from validated Seoul CSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .quality import AREA_KEY, KEY, load_many, require_columns


def next_quarter(value: str) -> str:
    year, quarter = int(value[:4]), int(value[4])
    return f"{year + 1}1" if quarter == 4 else f"{year}{quarter + 1}"


def unique(frame: pd.DataFrame, key: list[str], name: str) -> pd.DataFrame:
    if frame.duplicated(key).any():
        raise ValueError(f"{name} 키 중복을 먼저 해결해야 합니다: {key}")
    return frame


def build_model_dataset(
    store_paths: list[Path],
    sales_paths: list[Path],
    footfall_paths: list[Path] | None = None,
) -> pd.DataFrame:
    stores, _ = load_many(store_paths)
    sales, _ = load_many(sales_paths)
    require_columns("점포", stores, KEY + ["store_count", "closure_count"])
    require_columns("매출", sales, KEY + ["sales_amount", "sales_count"])

    stores = unique(stores, KEY, "점포").copy()
    sales = unique(sales, KEY, "매출")
    table = stores.merge(
        sales[KEY + ["sales_amount", "sales_count"]],
        on=KEY,
        how="left",
        validate="one_to_one",
    )
    table["sales_missing"] = table["sales_amount"].isna().astype("int8")

    if footfall_paths:
        footfall, _ = load_many(footfall_paths)
        require_columns("유동인구", footfall, AREA_KEY + ["footfall_count"])
        footfall = unique(footfall, AREA_KEY, "유동인구")
        table = table.merge(
            footfall[AREA_KEY + ["footfall_count"]],
            on=AREA_KEY,
            how="left",
            validate="many_to_one",
        )
        table["footfall_missing"] = table["footfall_count"].isna().astype("int8")

    table = table.sort_values(KEY).reset_index(drop=True)
    groups = table.groupby(["area_code", "industry_code"], sort=False)
    observed_next = groups["quarter"].shift(-1)
    future_closures = groups["closure_count"].shift(-1)
    expected_next = table["quarter"].map(next_quarter)
    table["target_available"] = observed_next.eq(expected_next).fillna(False).astype("int8")
    table["closure_next_q"] = (future_closures > 0).where(
        table["target_available"].eq(1)
    ).astype("Int8")

    return table
