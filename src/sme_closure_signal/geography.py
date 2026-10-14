"""Download official area geometry and audit district coverage without spatial inference."""

from __future__ import annotations

import hashlib
import json
import struct
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from .modeling import metrics


AREA_PAGE = "https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do"
AREA_DOWNLOAD = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false"


def download_areas(output: Path) -> None:
    body = urllib.parse.urlencode({"infId": "OA-15560", "seq": "5", "infSeq": "3", "seqNo": ""}).encode()
    request = urllib.request.Request(AREA_DOWNLOAD, data=body, headers={"Referer": AREA_PAGE})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read()
    output.parent.mkdir(parents=True, exist_ok=True)
    if payload[:2] != b"PK":
        raise ValueError("상권 영역 응답이 ZIP이 아닙니다. 공식 파일 목록을 재확인하세요.")
    output.write_bytes(payload)
    retrieved = datetime.now(ZoneInfo("Asia/Seoul"))
    provenance = {"source_page": AREA_PAGE, "retrieved_date": retrieved.date().isoformat(),
                  "retrieved_at": retrieved.isoformat(), "timezone": "Asia/Seoul",
                  "archive_sha256": hashlib.sha256(payload).hexdigest()}
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def area_retrieval_metadata(archive: Path) -> dict[str, object]:
    source = archive.with_suffix(archive.suffix + ".provenance.json")
    if not source.exists():
        return {"retrieved_date": None, "retrieved_at": None}
    metadata = json.loads(source.read_text(encoding="utf-8"))
    if metadata.get("archive_sha256") != hashlib.sha256(archive.read_bytes()).hexdigest():
        raise ValueError("영역 파일과 수집 메타데이터의 SHA-256이 다릅니다.")
    return {name: metadata.get(name) for name in ["retrieved_date", "retrieved_at"]}


def read_dbf(payload: bytes, encoding: str) -> pd.DataFrame:
    """Read the character/numeric attributes of the official dBase geometry table."""
    if len(payload) < 33:
        raise ValueError("DBF 헤더가 잘렸습니다.")
    count = struct.unpack_from("<I", payload, 4)[0]
    header, record_length = struct.unpack_from("<HH", payload, 8)
    if header < 33 or header > len(payload) or (header - 33) % 32 or payload[header - 1] != 13:
        raise ValueError("DBF 필드 헤더가 올바르지 않습니다.")
    fields = []
    for offset in range(32, header - 1, 32):
        name = payload[offset:offset + 11].split(b"\0")[0].decode("ascii")
        kind, width = chr(payload[offset + 11]), payload[offset + 16]
        if kind not in {"C", "N", "F"}:
            raise ValueError(f"지원하지 않는 DBF 필드 형식: {kind}")
        fields.append((name, kind, width))
    if sum(width for _, _, width in fields) + 1 != record_length or len(payload) < header + count * record_length:
        raise ValueError("DBF 레코드 길이가 일치하지 않습니다.")
    rows = []
    for index in range(count):
        record = payload[header + index * record_length:header + (index + 1) * record_length]
        if record[:1] == b"*":
            continue
        position, row = 1, {}
        for name, kind, width in fields:
            value = record[position:position + width].decode(encoding).strip()
            row[name] = (float(value) if value else None) if kind in {"N", "F"} else value
            position += width
        rows.append(row)
    return pd.DataFrame(rows)


def district_audit(archive: Path, predictions: Path, model_metadata: Path, output: Path) -> dict[str, object]:
    retrieval = area_retrieval_metadata(archive)
    with zipfile.ZipFile(archive) as source:
        cpg = source.read(next(name for name in source.namelist() if name.endswith(".cpg"))).decode().strip()
        attributes = read_dbf(source.read(next(name for name in source.namelist() if name.endswith(".dbf"))), cpg)
    mapping = attributes.rename(columns={"TRDAR_CD": "area_code", "TRDAR_CD_N": "area_name",
                                         "SIGNGU_CD": "district_code", "SIGNGU_CD_": "district_name", "RELM_AR": "area_sq_m"})
    columns = ["area_code", "area_name", "district_code", "district_name", "area_sq_m"]
    mapping = mapping[columns]
    if mapping.area_code.duplicated().any() or mapping[columns[:4]].isna().any().any() or mapping[columns[:4]].eq("").any().any():
        raise ValueError("상권-자치구 매핑의 키 중복·결측을 해결하세요.")
    scores = pd.read_csv(predictions, dtype={"quarter": str, "area_code": str, "industry_code": str})
    if scores.duplicated(["quarter", "area_code", "industry_code"]).any():
        raise ValueError("평가 예측 키가 중복됩니다.")
    metadata = json.loads(model_metadata.read_text(encoding="utf-8"))
    joined = scores.merge(mapping, on="area_code", how="left", validate="many_to_one", indicator=True)
    matched = joined["_merge"].eq("both")
    output.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(output / "area_district_mapping.csv", index=False, encoding="utf-8-sig")
    rows = []
    for district, part in joined.loc[matched].groupby("district_code"):
        for quarter in ["all"] + sorted(part.quarter.unique().tolist()):
            subset = part if quarter == "all" else part.loc[part.quarter.eq(quarter)]
            rows.append({"district_code": district, "district_name": part.district_name.iloc[0], "quarter": quarter,
                         **metrics(subset.closure_next_q, subset.policy_score.to_numpy(), metadata["global_threshold"])})
    pd.DataFrame(rows).to_csv(output / "district_performance.csv", index=False, encoding="utf-8-sig")
    report = {"dataset_id": "OA-15560", "source_page": AREA_PAGE, "license": "KOGL Type 1, attribution required",
              **retrieval, "audit_date": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
              "timezone": "Asia/Seoul", "file_modified_date_shown": "2023-10-23",
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "mapping_rows": len(mapping),
              "mapping_districts": int(mapping.district_code.nunique()), "prediction_rows": len(scores),
              "matched_prediction_rows": int(matched.sum()), "match_rate": float(matched.mean()),
              "unmatched_areas": sorted(joined.loc[~matched, "area_code"].unique().tolist()),
              "selected_family": metadata["selected_family"],
              "limitations": ["Area snapshot is not a quarter-versioned boundary history", "Used for subgroup audit only, never for model features",
                              "No geometry-based interpolation or name-based inferred mapping", "No refitting or independent period validation"]}
    (output / "provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
