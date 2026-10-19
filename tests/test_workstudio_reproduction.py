import pandas as pd
import pytest

from sme_closure_signal.workstudio_reproduction import reproduce


def test_missing_key_is_rejected_before_string_conversion():
    frame = pd.DataFrame({"quarter": [None], "area_code": ["A"], "industry_code": ["I"]})
    with pytest.raises(ValueError, match="missing"):
        reproduce([frame])


def test_duplicate_keys_across_inputs_are_rejected():
    frame = pd.DataFrame({"quarter": ["20241"], "area_code": ["A"], "industry_code": ["I"]})
    with pytest.raises(ValueError, match="unique"):
        reproduce([frame, frame.copy()])


def test_small_valid_partitions_work_without_fixed_row_counts():
    frame = pd.DataFrame({
        "quarter": ["20241", "20241", "20251", "20251"],
        "area_code": ["A", "B", "A", "B"], "industry_code": ["I"] * 4,
        "log_stores": [1., 2., 1., 2.], "log_closures": [0., 1., 0., 1.],
        "log_openings": [0.] * 4, "closure_next_q": [0, 1, 0, 1],
    })
    result = reproduce([frame])
    assert result.split.tolist() == ["validation"]
    assert result.rows.tolist() == [2]
    frame.loc[frame.quarter.eq("20251"), "closure_next_q"] = 0
    with pytest.raises(ValueError, match="both classes"):
        reproduce([frame])
