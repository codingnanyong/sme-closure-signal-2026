"""Read and validate local Seoul commercial-area source data."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


KEY = ["quarter", "area_code", "industry_code"]
AREA_KEY = ["quarter", "area_code"]

ALIASES = {
    "기준_년분기_코드": "quarter",
    "stdr_yyqu_cd": "quarter",
    "STDR_YYQU_CD": "quarter",
    "상권_코드": "area_code",
    "trdar_cd": "area_code",
    "TRDAR_CD": "area_code",
    "상권_코드_명": "area_name",
    "trdar_cd_nm": "area_name",
    "TRDAR_CD_NM": "area_name",
    "서비스_업종_코드": "industry_code",
    "svc_induty_cd": "industry_code",
    "SVC_INDUTY_CD": "industry_code",
    "서비스_업종_코드_명": "industry_name",
    "svc_induty_cd_nm": "industry_name",
    "SVC_INDUTY_CD_NM": "industry_name",
    "점포_수": "store_count",
    "stor_co": "store_count",
    "STOR_CO": "store_count",
    "유사_업종_점포_수": "similar_store_count",
    "similr_induty_stor_co": "similar_store_count",
    "SIMILR_INDUTY_STOR_CO": "similar_store_count",
    "개업_율": "opening_rate",
    "opbiz_rt": "opening_rate",
    "OPBIZ_RT": "opening_rate",
    "개업_점포_수": "opening_count",
    "opbiz_stor_co": "opening_count",
    "OPBIZ_STOR_CO": "opening_count",
    "폐업_률": "closure_rate",
    "clsbiz_rt": "closure_rate",
    "CLSBIZ_RT": "closure_rate",
    "폐업_점포_수": "closure_count",
    "clsbiz_stor_co": "closure_count",
    "CLSBIZ_STOR_CO": "closure_count",
    "당월_매출_금액": "sales_amount",
    "thsmon_selng_amt": "sales_amount",
    "THSMON_SELNG_AMT": "sales_amount",
    "당월_매출_건수": "sales_count",
    "thsmon_selng_co": "sales_count",
    "THSMON_SELNG_CO": "sales_count",
    "총_유동인구_수": "footfall_count",
    "tot_flpop_co": "footfall_count",
    "TOT_FLPOP_CO": "footfall_count",
}


def read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            frame = pd.read_csv(path, encoding=encoding, low_memory=False)
            frame.attrs["encoding"] = encoding
            return frame
        except UnicodeDecodeError as error:
            last_error = error
    raise RuntimeError(f"지원 인코딩으로 읽을 수 없습니다: {path}") from last_error


def canonicalize(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(columns={column: ALIASES.get(column, column) for column in frame.columns})
    for column in ("quarter", "area_code", "industry_code"):
        if column in renamed.columns:
            renamed[column] = renamed[column].astype("string").str.strip()
    return renamed


def load_many(paths: Iterable[Path]) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    frames: list[pd.DataFrame] = []
    sources: list[dict[str, object]] = []
    for path in paths:
        raw = read_csv(path)
        sources.append(
            {
                "file": path.name,
                "rows": int(len(raw)),
                "columns": int(len(raw.columns)),
                "encoding": raw.attrs["encoding"],
            }
        )
        frames.append(canonicalize(raw))
    return pd.concat(frames, ignore_index=True), sources


def require_columns(name: str, frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} 필수 컬럼 누락: {', '.join(missing)}")


def dataset_summary(frame: pd.DataFrame, key: list[str]) -> dict[str, object]:
    duplicate_count = int(frame.duplicated(key, keep=False).sum())
    quarters = sorted(frame["quarter"].dropna().astype(str).unique().tolist())
    return {
        "rows": int(len(frame)),
        "quarters": quarters,
        "unique_areas": int(frame["area_code"].nunique(dropna=True)),
        "duplicate_key_rows": duplicate_count,
        "null_key_rows": int(frame[key].isna().any(axis=1).sum()),
    }


def key_coverage(left: pd.DataFrame, right: pd.DataFrame, key: list[str]) -> dict[str, object]:
    left_keys = left[key].drop_duplicates()
    right_keys = right[key].drop_duplicates()
    matched = left_keys.merge(right_keys, on=key, how="inner")
    return {
        "left_unique_keys": int(len(left_keys)),
        "right_unique_keys": int(len(right_keys)),
        "matched_keys": int(len(matched)),
        "left_match_rate": round(len(matched) / len(left_keys), 6) if len(left_keys) else None,
        "right_match_rate": round(len(matched) / len(right_keys), 6) if len(right_keys) else None,
    }


def continuity(frame: pd.DataFrame, earlier: str, later: str) -> dict[str, object]:
    earlier_codes = set(frame.loc[frame["quarter"] == earlier, "area_code"].dropna())
    later_codes = set(frame.loc[frame["quarter"] == later, "area_code"].dropna())
    retained = earlier_codes & later_codes
    return {
        "earlier": earlier,
        "later": later,
        "earlier_areas": len(earlier_codes),
        "later_areas": len(later_codes),
        "retained_areas": len(retained),
        "earlier_retention_rate": round(len(retained) / len(earlier_codes), 6)
        if earlier_codes
        else None,
        "later_retention_rate": round(len(retained) / len(later_codes), 6)
        if later_codes
        else None,
    }


def target_summary(stores: pd.DataFrame) -> dict[str, object]:
    closure_rate = pd.to_numeric(stores["closure_rate"], errors="coerce")
    closure_count = pd.to_numeric(stores["closure_count"], errors="coerce")
    store_count = pd.to_numeric(stores["store_count"], errors="coerce")
    current_store_rate = closure_count.div(store_count.where(store_count > 0)).mul(100)
    current_plus_closed = store_count + closure_count
    current_plus_closed_rate = closure_count.div(
        current_plus_closed.where(current_plus_closed > 0)
    ).mul(100)

    def reconstruction_mae(candidate: pd.Series) -> float | None:
        comparable = closure_rate.notna() & candidate.notna()
        if not comparable.any():
            return None
        return round(float((closure_rate[comparable] - candidate[comparable]).abs().mean()), 6)

    quantiles = closure_rate.quantile([0.5, 0.9, 0.95, 0.99, 0.999, 1.0])
    return {
        "closure_rate_nulls": int(closure_rate.isna().sum()),
        "closure_count_nulls": int(closure_count.isna().sum()),
        "positive_closure_rows": int((closure_count > 0).sum()),
        "positive_closure_share": round(float((closure_count > 0).mean()), 6),
        "zero_store_rows": int((store_count == 0).sum()),
        "closure_count_gt_store_count_rows": int((closure_count > store_count).sum()),
        "closure_rate_gt_100_rows": int((closure_rate > 100).sum()),
        "closure_rate_min": float(closure_rate.min()),
        "closure_rate_max": float(closure_rate.max()),
        "closure_rate_median": float(closure_rate.median()),
        "closure_rate_quantiles": {
            str(index): float(value) for index, value in quantiles.items()
        },
        "reconstruction_mae": {
            "closure_count / current_store_count * 100": reconstruction_mae(current_store_rate),
            "closure_count / (current_store_count + closure_count) * 100": reconstruction_mae(
                current_plus_closed_rate
            ),
        },
        "note": (
            "공개 폐업률은 100을 넘을 수 있고 다운로드 스키마만으로 분모가 완전히 "
            "정의되지 않는다. 제공기관 정의를 확인하기 전에는 확률이 아닌 지표로만 "
            "해석하고, 모델 타깃은 시차가 명시된 노출량 대비 미래 폐업 건수 또는 "
            "폐업 발생 여부로 정의한다."
        ),
    }


def validate_sources(
    store_paths: list[Path],
    sales_paths: list[Path],
    footfall_paths: list[Path] | None = None,
) -> dict[str, object]:
    stores, store_sources = load_many(store_paths)
    sales, sales_sources = load_many(sales_paths)
    require_columns("점포", stores, KEY + ["store_count", "closure_rate", "closure_count"])
    require_columns("매출", sales, KEY + ["sales_amount", "sales_count"])

    common_quarters = sorted(set(stores["quarter"]) & set(sales["quarter"]))
    stores_common = stores[stores["quarter"].isin(common_quarters)]
    sales_common = sales[sales["quarter"].isin(common_quarters)]

    report: dict[str, object] = {
        "store_sources": store_sources,
        "sales_sources": sales_sources,
        "stores": dataset_summary(stores, KEY),
        "sales": dataset_summary(sales, KEY),
        "common_quarters": common_quarters,
        "store_sales_coverage": key_coverage(sales_common, stores_common, KEY),
        "area_continuity_2024Q4_to_2025Q1": {
            "stores": continuity(stores, "20244", "20251"),
            "sales": continuity(sales, "20244", "20251"),
        },
        "target": target_summary(stores),
    }

    if footfall_paths:
        footfall, footfall_sources = load_many(footfall_paths)
        require_columns("유동인구", footfall, AREA_KEY + ["footfall_count"])
        footfall_common_quarters = sorted(set(footfall["quarter"]) & set(stores["quarter"]))
        footfall_common = footfall[footfall["quarter"].isin(footfall_common_quarters)]
        store_areas = stores[stores["quarter"].isin(footfall_common_quarters)]
        sales_areas = sales[sales["quarter"].isin(footfall_common_quarters)]
        report["footfall_sources"] = footfall_sources
        report["footfall"] = dataset_summary(footfall, AREA_KEY)
        report["footfall_common_quarters"] = footfall_common_quarters
        report["footfall_store_area_coverage"] = key_coverage(store_areas, footfall_common, AREA_KEY)
        report["footfall_sales_area_coverage"] = key_coverage(sales_areas, footfall_common, AREA_KEY)

    return report
