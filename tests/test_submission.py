import pytest

from sme_closure_signal.submission import application_counts


def test_application_counts_requires_all_five_complete_sections():
    text = "\n".join(f"## {i}. 항목\n" + "가" * 300 for i in range(1, 6))
    assert application_counts(text) == [300] * 5
    with pytest.raises(ValueError, match="5개"):
        application_counts("## 1. 항목\n내용")
    with pytest.raises(ValueError, match="300자"):
        application_counts(text.replace("가" * 300, "짧음", 1))
