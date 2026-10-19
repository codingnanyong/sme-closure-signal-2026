from pathlib import Path
import urllib.error

import pytest
import pandas as pd

import sme_closure_signal.acquisition as acquisition


def test_sample_key_is_not_accepted_for_full_collection(monkeypatch):
    monkeypatch.setenv("SEOUL_OPEN_DATA_API_KEY", "sample")
    with pytest.raises(ValueError, match="설정"):
        acquisition.local_api_key(Path("unused"))


def test_api_failure_does_not_expose_key_or_downgrade_https(monkeypatch):
    urls = []
    def fail(url, **kwargs):
        urls.append(url)
        raise urllib.error.URLError("synthetic-secret-in-underlying-error")
    monkeypatch.setattr(acquisition.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError) as error:
        acquisition.fetch_official_page("synthetic-secret-in-underlying-error", "20241", 1, 1000)
    assert len(urls) == 1 and urls[0].startswith("https://")
    assert "synthetic-secret-in-underlying-error" not in str(error.value)
    assert error.value.__suppress_context__


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


def test_collect_sources_uses_live_file_ids_and_preserves_zip_bytes(monkeypatch, tmp_path):
    import hashlib
    import io
    import json
    import zipfile
    import urllib.parse

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("nested/source.csv", b"quarter,value\n20241,7\n")
    calls = []
    def open_source(request, **kwargs):
        calls.append(request)
        if isinstance(request, str):
            html = '<input name="infSeq" value="9"><span title="source_2024년.zip" onclick="downloadFile(\'123\')"></span>'
            return io.BytesIO(html.encode("utf-8"))
        assert urllib.parse.parse_qs(request.data.decode())["seq"] == ["123"]
        return io.BytesIO(payload.getvalue())
    monkeypatch.setattr(acquisition.urllib.request, "urlopen", open_source)
    result = acquisition.collect_sources([2024], tmp_path)
    assert len(calls) == 4 and len(result["files"]) == 2
    for record in result["files"]:
        archive = Path(record["archive"])
        assert archive.read_bytes() == payload.getvalue()
        assert record["archive_sha256"] == hashlib.sha256(payload.getvalue()).hexdigest()
        assert Path(record["csv"]).read_bytes() == b"quarter,value\n20241,7\n"
        assert json.loads(archive.with_suffix(".zip.provenance.json").read_text(encoding="utf-8"))["year"] == 2024
