import pandas as pd
import pytest

from sme_closure_signal.history import extend_store_panel


def test_history_extension_joins_consecutive_target_and_does_not_bridge_gap():
    history = pd.DataFrame({"quarter": ["20234", "20233"], "area_code": ["A", "B"], "industry_code": "I",
                            "store_count": 10, "closure_count": 0, "opening_count": 1})
    current = pd.DataFrame({"quarter": ["20241", "20241"], "area_code": ["A", "B"], "industry_code": "I",
                            "store_count": 9, "closure_count": 2, "opening_count": 0})
    result = extend_store_panel(current, history)
    assert len(result) == 1
    assert result.iloc[0].area_code == "A"
    assert result.iloc[0].closure_next_q == 1
    assert pd.api.types.is_integer_dtype(result.closure_next_q)
    with pytest.raises(ValueError, match="중복"):
        extend_store_panel(current, current)
