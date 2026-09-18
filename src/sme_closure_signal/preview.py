"""Fetch public Seoul footfall Sheet-preview rows for validation only.

The Seoul dataset page exposes a 1,000-row Sheet preview without an API key.
This helper retrieves selected quarters and writes a local CSV. The endpoint is
a preview interface rather than the documented Open API, so production use
should switch to an issued Seoul Open Data API key or official download file.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd


ENDPOINT = "https://data.seoul.go.kr/dataList/dataView.do"
DATASET_ID = "OA-15568"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quarters", nargs="+", required=True)
    return parser.parse_args()


def decode_preview(payload: str) -> dict[str, object]:
    # The preview returns JavaScript object notation with unquoted ASCII keys.
    normalized = re.sub(
        r"([,{])\s*([A-Za-z_][A-Za-z0-9_]*):",
        r'\1"\2":',
        payload.strip(),
    )
    normalized = re.sub(r",\s*]", "]", normalized)
    return json.loads(normalized)


def fetch_page(quarter: str, page: int) -> dict[str, object]:
    params = {
        "onepagerow": "1000",
        "srvType": "S",
        "infId": DATASET_ID,
        "serviceKind": "0",
        "pageNo": str(page),
        "ssUserId": "SAMPLE_VIEW",
        "strWhere": "",
        "strOrderby": "STDR_YYQU_CD DESC",
        "filterCol": "STDR_YYQU_CD",
        "txtFilter": quarter,
    }
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return decode_preview(response.read().decode("utf-8"))


def main() -> None:
    args = parse_args()
    rows: list[dict[str, object]] = []
    for quarter in args.quarters:
        page = 1
        while True:
            result = fetch_page(quarter, page)
            rows.extend(result["list"])
            page_info = result["page"]
            if page >= int(page_info["pageCount"]):
                break
            page += 1

    raw_row_count = len(rows)
    frame = pd.DataFrame(rows)
    frame = frame.drop_duplicates(["STDR_YYQU_CD", "TRDAR_CD"])
    frame = frame.drop(columns=["RONUM"], errors="ignore")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"raw_rows={raw_row_count}")
    print(f"deduplicated_rows={len(frame)}")
    print(f"quarters={sorted(frame['STDR_YYQU_CD'].astype(str).unique().tolist())}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
