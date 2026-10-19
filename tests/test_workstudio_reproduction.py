import pandas as pd
import pytest

from sme_closure_signal.workstudio_reproduction import reproduce


def test_missing_key_is_rejected_before_string_conversion():
    frame = pd.DataFrame({"quarter": [None], "area_code": ["A"], "industry_code": ["I"]})
    with pytest.raises(AssertionError):
        reproduce([frame])


def test_duplicate_keys_across_inputs_are_rejected():
    frame = pd.DataFrame({"quarter": ["20241"], "area_code": ["A"], "industry_code": ["I"]})
    with pytest.raises(AssertionError):
        reproduce([frame, frame.copy()])
