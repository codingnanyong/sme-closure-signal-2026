import pytest

from pathlib import Path
from sme_closure_signal.submission import application_counts, external_pdf_links, archive_package
from sme_closure_signal.submission import digest, verified_workstudio_execution


def test_application_counts_requires_all_five_complete_sections():
    text = "\n".join(f"## {i}. 항목\n" + "가" * 300 for i in range(1, 6))
    assert application_counts(text) == [300] * 5
    with pytest.raises(ValueError, match="5개"):
        application_counts("## 1. 항목\n내용")
    with pytest.raises(ValueError, match="300자"):
        application_counts(text.replace("가" * 300, "짧음", 1))
    assert application_counts(text + "\n## 공개 및 검토 기록\n메타데이터") == [300] * 5
    with pytest.raises(ValueError, match="5개"):
        application_counts(text + "\n## 6. 추가 항목\n" + "가" * 300)


def test_package_references_pdf_without_redistributing_file():
    root = Path.cwd()
    result = external_pdf_links("[공고](../../references/notice.pdf)", root / "docs/kor/project/review.md", root)
    assert result == "[공고](https://github.com/codingnanyong/sme-closure-signal-2026/blob/main/docs/references/notice.pdf)"


def test_zip_contains_only_explicit_manifest_files(monkeypatch):
    written = []
    class Bundle:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def write(self, source, arcname): written.append(arcname)
    monkeypatch.setattr("sme_closure_signal.submission.zipfile.ZipFile", Bundle)
    archive_package(Path("outputs/submission/test"), ["current.csv", "manifest.json"])
    assert written == ["current.csv", "manifest.json"]
    with pytest.raises(ValueError, match="경로"):
        archive_package(Path("outputs/submission/test"), ["../outside.csv"])


@pytest.mark.parametrize("change", [None, "input", "result", "status"])
def test_execution_evidence_rejects_stale_or_failed_runs(tmp_path, change):
    import json

    names = ["train", "validation", "test"]
    result_names = ["studio_metrics.csv", "local_script_metrics.csv", "environment_comparison.csv"]
    files = {}
    for name in [f"{name}.csv" for name in names] + result_names:
        path = tmp_path / name
        path.write_text("synthetic,value\nA,1\n", encoding="utf-8")
        files[name] = digest(path)
    record = {"execution_status": "success", "input_count": 3, "files": files,
              "model_equivalence": "not_exact"}
    exports = {name: {"sha256": files[f"{name}.csv"]} for name in names}
    if change == "input":
        exports["train"]["sha256"] = "different-input"
    elif change == "result":
        (tmp_path / "studio_metrics.csv").write_text("changed", encoding="utf-8")
    elif change == "status":
        record["execution_status"] = "failed"
    (tmp_path / "execution_record.json").write_text(json.dumps(record), encoding="utf-8")
    if change is None:
        assert verified_workstudio_execution(tmp_path, exports)["model_equivalence"] == "not_exact"
    else:
        with pytest.raises(ValueError):
            verified_workstudio_execution(tmp_path, exports)


def test_absent_execution_record_does_not_claim_studio_success(tmp_path):
    assert verified_workstudio_execution(tmp_path, {}) is None
