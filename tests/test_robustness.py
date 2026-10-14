import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from sme_closure_signal.robustness import WeightedAveragePrecision, paired_area_bootstrap, select_trial


@pytest.mark.parametrize("seed", [0, 198, 2026])
def test_cached_weighted_ap_matches_sklearn_with_ties_and_omitted_rows(seed):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, 100)
    score = rng.integers(0, 5, 100) / 5
    weights = rng.integers(0, 4, 100)
    assert WeightedAveragePrecision(y, score)(weights) == pytest.approx(
        average_precision_score(y, score, sample_weight=weights), abs=1e-12
    )


def test_paired_cluster_bootstrap_is_repeatable_and_identical_models_have_zero_difference():
    frame = pd.DataFrame({"area_code": ["A", "A", "B", "B", "C", "C"],
                          "closure_next_q": [0, 1, 1, 0, 0, 1],
                          "full": [0.1, 0.9, 0.7, 0.3, 0.4, 0.6]})
    frame["same"] = frame["full"]
    intervals, draws = paired_area_bootstrap(frame, ["full", "same"], 20, 198)
    repeated_intervals, repeated_draws = paired_area_bootstrap(frame, ["full", "same"], 20, 198)
    pd.testing.assert_frame_equal(intervals, repeated_intervals)
    pd.testing.assert_frame_equal(draws, repeated_draws)
    difference = intervals.loc[intervals.comparison.eq("full - same")].iloc[0]
    assert difference[["estimate", "lower95", "upper95"]].tolist() == [0, 0, 0]
    # Cluster multiplicities must be shared by all rows and models in a draw.
    for counts, row in zip(np.random.default_rng(198).multinomial(3, [1 / 3] * 3, size=20), draws.itertuples()):
        assert row.full == pytest.approx(average_precision_score(
            frame.closure_next_q, frame.full, sample_weight=np.repeat(counts, 2)))


def test_trial_selection_does_not_read_test_scores():
    trials = [{"C": 0.1, "validation_ap": 0.4, "test_ap": 0.99},
              {"C": 1.0, "validation_ap": 0.5, "test_ap": 0.1}]
    assert select_trial(trials)["C"] == 1.0
