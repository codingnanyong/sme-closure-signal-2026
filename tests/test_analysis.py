import pandas as pd

from sme_closure_signal.analysis import summarize_target


def test_summarize_target_returns_null_share_when_no_target_is_available() -> None:
    frame = pd.DataFrame(
        {
            "quarter": ["20241"],
            "target_available": [0],
            "closure_next_q": pd.array([pd.NA], dtype="Int8"),
        }
    )

    assert summarize_target(frame) == {
        "rows": 0,
        "positive_share": None,
        "by_quarter": {},
    }
