"""Collect complete official Seoul footfall quarters using a locally configured key."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .quality import AREA_KEY, KEY, canonicalize, read_csv


SERVICE = "VwsmTrdarFlpopQq"
# Official examples use HTTP. HTTPS on ports 8088/443 failed our 2026-10-14
# connection checks; keep HTTPS as default and never downgrade credentials silently.
API_BASE = "https://openapi.seoul.go.kr:8088"
OFFICIAL_HTTP_API = "http://openapi.seoul.go.kr:8088"
SOURCE = "https://data.seoul.go.kr/dataList/OA-15568/S/1/datasetView.do?tab=A"


def local_api_key(env_file: Path) -> str:
    key = os.environ.get("SEOUL_OPEN_DATA_API_KEY", "").strip()
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.strip().partition("=")
            if separator and name.strip() == "SEOUL_OPEN_DATA_API_KEY":
                key = value.strip().strip('"').strip("'")
                break
    if not key or key.lower() in {"sample", "your_api_key_here"}:
        raise ValueError("SEOUL_OPEN_DATA_API_KEY를 로컬 .env 또는 환경변수에 설정하세요. 키는 출력하지 않습니다.")
    return key


def fetch_official_page(key: str, quarter: str, start: int, end: int, *, allow_http: bool = False) -> dict[str, object]:
    base = OFFICIAL_HTTP_API if allow_http else API_BASE
    url = f"{base}/{urllib.parse.quote(key, safe='')}/json/{SERVICE}/{start}/{end}/{quarter}"
    try:
        with urllib.request.urlopen(url, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        # URL-bearing exception tracebacks may expose the key embedded in the path.
        raise RuntimeError("공식 API 요청에 실패했습니다. 네트워크·인증·서비스 상태를 확인하세요.") from None


def collect_footfall(quarters: list[str], env_file: Path, output: Path, *, allow_http: bool = False) -> dict[str, object]:
    if not quarters or len(set(quarters)) != len(quarters) or any(not re.fullmatch(r"\d{4}[1-4]", q) for q in quarters):
        raise ValueError("중복 없는 YYYYQ 분기 목록이 필요합니다.")
    key = local_api_key(env_file)
    all_rows, counts = [], {}
    for quarter in quarters:
        start, expected, rows = 1, None, []
        while expected is None or start <= expected:
            result = (fetch_official_page(key, quarter, start, start + 999, allow_http=True) if allow_http
                      else fetch_official_page(key, quarter, start, start + 999))
            service = result.get(SERVICE, {})
            code = service.get("RESULT", result.get("RESULT", {})).get("CODE")
            if code != "INFO-000":
                raise ValueError("공식 API가 정상 자료를 반환하지 않았습니다. 인증키·분기·서비스 상태를 확인하세요.")
            total = int(service["list_total_count"])
            if total <= 0 or expected is not None and total != expected:
                raise ValueError("공식 API 총 건수가 없거나 수집 중 변경되었습니다.")
            expected = total
            page = service.get("row", [])
            if len(page) != min(1000, expected - start + 1):
                raise ValueError("공식 API 페이지 길이가 총 건수와 일치하지 않습니다.")
            rows.extend(page)
            start += 1000
        table = canonicalize(pd.DataFrame(rows))
        required = AREA_KEY + ["footfall_count"]
        if any(c not in table for c in required) or table[required].isna().any().any():
            raise ValueError("공식 유동인구 필수 컬럼·값이 누락되었습니다.")
        if table.duplicated(AREA_KEY).any() or not table.quarter.eq(quarter).all():
            raise ValueError("공식 유동인구의 중복 키 또는 요청 분기 불일치가 있습니다.")
        values = pd.to_numeric(table.footfall_count, errors="coerce")
        if values.isna().any() or values.lt(0).any():
            raise ValueError("유동인구 수가 숫자가 아니거나 음수입니다.")
        counts[quarter] = len(table)
        all_rows.extend(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(all_rows)
    temporary = output.with_suffix(output.suffix + ".partial")
    table.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(output)
    provenance = {"source_page": SOURCE, "service": SERVICE, "interface": "official_open_api", "preview": False,
                  "retrieved_date": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(), "timezone": "Asia/Seoul", "quarters": counts,
                  "rows": len(table), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                  "geography": "Seoul commercial area", "industry_dimension": False,
                  "license": "KOGL Type 1; attribution required", "api_key_recorded": False,
                  "transport": "http_explicit_opt_in" if allow_http else "https",
                  "limitations": ["No historical release-date verification", "Population is area-level, not industry-specific customers"]}
    output.with_suffix(output.suffix + ".provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return provenance


class StoreDownloadParser(HTMLParser):
    def __init__(self, year: int):
        super().__init__()
        self.year, self.sequence, self.inf_sequence = year, None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "infSeq":
            self.inf_sequence = attrs.get("value")
        if tag == "span" and f"{self.year}년.zip" in attrs.get("title", ""):
            match = re.search(r"downloadFile\('(\d+)'\)", attrs.get("onclick", ""))
            if match:
                self.sequence = match.group(1)


def collect_sources(years: list[int], data_root: Path) -> dict[str, object]:
    """Recover official annual stores/sales archives and provenance from live listings."""
    if not years or len(set(years)) != len(years) or any(year not in {2024, 2025} for year in years):
        raise ValueError("중복 없는 2024·2025년 목록이 필요합니다.")
    records = []
    for kind, identifier in [("stores", "OA-15577"), ("sales", "OA-15572")]:
        page = f"https://data.seoul.go.kr/dataList/{identifier}/A/1/datasetView.do"
        with urllib.request.urlopen(page, timeout=45) as response:
            html = response.read().decode("utf-8")
        for year in years:
            parser = StoreDownloadParser(year)
            parser.feed(html)
            if not parser.sequence or not parser.inf_sequence:
                raise ValueError(f"공식 파일 항목을 찾지 못했습니다: {kind} {year}")
            body = urllib.parse.urlencode({"infId": identifier, "seq": parser.sequence,
                                          "infSeq": parser.inf_sequence}).encode()
            request = urllib.request.Request(
                "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false",
                data=body, headers={"Referer": page})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            archive = data_root / "raw/seoul" / kind / f"{kind}-{year}.zip"
            with zipfile.ZipFile(io.BytesIO(payload)) as source:
                members = [name for name in source.namelist() if name.lower().endswith(".csv")]
                if len(members) != 1:
                    raise ValueError("연도별 ZIP에 CSV가 정확히 하나 있어야 합니다.")
                csv_payload = source.read(members[0])  # Read verifies the CSV member CRC.
                csv = data_root / "interim/seoul" / kind / f"{kind}-{year}.csv"
                archive.parent.mkdir(parents=True, exist_ok=True)
                csv.parent.mkdir(parents=True, exist_ok=True)
                for target, content in [(archive, payload), (csv, csv_payload)]:
                    temporary = target.with_suffix(target.suffix + ".partial")
                    temporary.write_bytes(content)
                    temporary.replace(target)
            record = {"source_page": page, "dataset_id": identifier, "year": year,
                      "archive": str(archive), "csv": str(csv),
                      "archive_sha256": hashlib.sha256(payload).hexdigest(),
                      "csv_sha256": hashlib.sha256(csv_payload).hexdigest(),
                      "retrieved_date": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
                      "timezone": "Asia/Seoul", "geography": "Seoul commercial area",
                      "industry_granularity": "source service industry code", "time_granularity": "quarter",
                      "license": "KOGL Type 1; attribution required",
                      "limitations": ["Historical release dates not verified", "Aggregate observations, not individual businesses"]}
            archive.with_suffix(".zip.provenance.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            records.append(record)
    return {"files": records}


def collect_history(year: int, output: Path, current_dataset: Path) -> dict[str, object]:
    if year not in {2021, 2022, 2023}:
        raise ValueError("과거 기간 검토는 2021~2023년을 지원합니다.")
    page = "https://data.seoul.go.kr/dataList/OA-15577/A/1/datasetView.do"
    with urllib.request.urlopen(page, timeout=30) as response:
        html = response.read().decode("utf-8")
    parser = StoreDownloadParser(year)
    parser.feed(html)
    if not parser.sequence or not parser.inf_sequence:
        raise ValueError("공식 연도별 파일 항목을 확인할 수 없습니다.")
    body = urllib.parse.urlencode({"infId": "OA-15577", "seq": parser.sequence, "infSeq": parser.inf_sequence}).encode()
    request = urllib.request.Request("https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false", data=body, headers={"Referer": page})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"stores-{year}.zip"
    archive.write_bytes(payload)
    with zipfile.ZipFile(archive) as source:
        members = [name for name in source.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError("과거 점포 파일에 CSV가 정확히 하나 있어야 합니다.")
        csv = output / f"stores-{year}.csv"
        csv.write_bytes(source.read(members[0]))
    history = canonicalize(read_csv(csv))
    current = pd.read_csv(current_dataset, dtype={"quarter": str, "area_code": str, "industry_code": str}, low_memory=False)
    if any(column not in history for column in KEY + ["store_count", "closure_count", "opening_count"]):
        raise ValueError("과거 점포 자료의 필수 스키마가 다릅니다.")
    earlier = history.loc[history.quarter.eq(f"{year}4")]
    later_quarters = sorted(q for q in current.quarter.unique() if q > f"{year}4")
    if not later_quarters:
        raise ValueError("비교할 현재 기간이 없습니다.")
    later = current.loc[current.quarter.eq(later_quarters[0])]
    before, after = set(earlier.area_code), set(later.area_code)
    before_pairs = set(zip(earlier.area_code, earlier.industry_code))
    after_pairs = set(zip(later.area_code, later.industry_code))
    report = {"source_page": page, "dataset_id": "OA-15577", "year": year,
              "retrieved_date": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(), "timezone": "Asia/Seoul",
              "license": "KOGL Type 1; attribution required", "archive_sha256": hashlib.sha256(payload).hexdigest(),
              "csv_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(), "rows": len(history),
              "quarters": sorted(history.quarter.unique().tolist()), "duplicate_key_rows": int(history.duplicated(KEY).sum()),
              "null_key_rows": int(history[KEY].isna().any(axis=1).sum()), "unique_areas": int(history.area_code.nunique()),
              "boundary_comparison": {"earlier": f"{year}4", "later": later_quarters[0],
                                      "earlier_areas": len(before), "later_areas": len(after), "common_areas": len(before & after),
                                      "earlier_area_retention": len(before & after) / len(before) if before else None,
                                      "later_area_coverage": len(before & after) / len(after) if after else None,
                                      "earlier_area_industry_pairs": len(before_pairs), "later_area_industry_pairs": len(after_pairs),
                                      "common_area_industry_pairs": len(before_pairs & after_pairs)},
              "used_for_model_training": False, "limitations": ["Code overlap does not prove historical boundary-definition equivalence",
                                                                  "Earlier period is not an independent future holdout", "No performance improvement measured"]}
    (output / f"stores-{year}.provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
