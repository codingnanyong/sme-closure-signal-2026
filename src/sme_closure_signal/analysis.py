"""Summarize the observed next-quarter closure target by quarter."""

from __future__ import annotations

import pandas as pd


def summarize_target(frame: pd.DataFrame) -> dict[str, object]:
    observed = frame.loc[frame["target_available"].eq(1)].copy()
    by_quarter = observed.groupby("quarter")["closure_next_q"].agg(["count", "mean"])
    return {
        "rows": int(len(observed)),
        "positive_share": round(float(observed["closure_next_q"].mean()), 6),
        "by_quarter": {
            str(index): {"rows": int(row["count"]), "positive_share": round(float(row["mean"]), 6)}
            for index, row in by_quarter.iterrows()
        },
    }
