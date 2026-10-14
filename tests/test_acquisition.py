from pathlib import Path

import pytest
import pandas as pd

import sme_closure_signal.acquisition as acquisition


def test_sample_key_is_not_accepted_for_full_collection(monkeypatch):
    monkeypatch.setenv("SEOUL_OPEN_DATA_API_KEY", "sample")
    with pytest.raises(ValueError, match="설정"):
        acquisition.local_api_key(Path("unused"))


@pytest.mark.parametrize("case", ["short_page", "wrong_quarter", "duplicate", "api_error"])
def test_collector_rejects_incomplete_or_wrong_api_rows_before_writing(monkeypatch, case):
    monkeypatch.setattr(acquisition, "local_api_key", lambda _: "synthetic-test-key")
    quarter = "20242" if case == "wrong_quarter" else "20241"
    rows = [{"STDR_YYQU_CD": quarter, "TRDAR_CD": "A", "TOT_FLPOP_CO": 100}]
    if case == "duplicate":
        rows *= 2
    result = {acquisition.SERVICE: {"RESULT": {"CODE": "ERROR-001" if case == "api_error" else "INFO-000"},
                                  "list_total_count": 2 if case in {"short_page", "duplicate"} else 1, "row": rows}}
    monkeypatch.setattr(acquisition, "fetch_official_page", lambda *args: result)
    with pytest.raises(ValueError):
        acquisition.collect_footfall(["20241"], Path("unused"), Path("should-not-write.csv"))


def test_collector_fetches_all_pages_and_checks_complete_count(monkeypatch):
    monkeypatch.setattr(acquisition, "local_api_key", lambda _: "synthetic-test-key")
    calls, written = [], []
    def page(key, quarter, start, end):
        calls.append((quarter, start, end))
        rows = [{"STDR_YYQU_CD": quarter, "TRDAR_CD": f"{i:05}", "TOT_FLPOP_CO": i}
                for i in range(start, min(end, 1001) + 1)]
        return {acquisition.SERVICE: {"RESULT": {"CODE": "INFO-000"}, "list_total_count": 1001, "row": rows}}
    monkeypatch.setattr(acquisition, "fetch_official_page", page)
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, *a, **k: written.append(self.copy()))
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: None)
    monkeypatch.setattr(Path, "replace", lambda *a, **k: None)
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: b"synthetic-test-csv")
    monkeypatch.setattr(Path, "write_text", lambda *a, **k: None)
    report = acquisition.collect_footfall(["20241"], Path("unused"), Path("not-written.csv"))
    assert calls == [("20241", 1, 1000), ("20241", 1001, 2000)]
    assert len(written[0]) == report["rows"] == report["quarters"]["20241"] == 1001
    assert report["interface"] == "official_open_api" and report["preview"] is False


def test_history_download_parser_selects_only_requested_year():
    parser = acquisition.StoreDownloadParser(2023)
    parser.feed('<input name="infSeq" value="3"><span title="점포_2024년.zip" onclick="downloadFile(\'19\')"></span>'
                '<span title="점포_2023년.zip" onclick="downloadFile(\'18\')"></span>')
    assert parser.sequence == "18" and parser.inf_sequence == "3"
