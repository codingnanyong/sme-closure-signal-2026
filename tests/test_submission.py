import pytest

from pathlib import Path
from sme_closure_signal.submission import application_counts, external_pdf_links, archive_package


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
