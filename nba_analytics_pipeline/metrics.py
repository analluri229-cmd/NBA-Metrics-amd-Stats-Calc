from __future__ import annotations

import pandas as pd


def add_decision_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add decision-oriented metrics that are useful for team-facing analysis."""
    if df.empty:
        return df

    result = df.copy()
    result["decision_score"] = 0.0

    if "PTS" in result.columns:
        result["decision_score"] += result["PTS"] * 0.15
    if "AST" in result.columns:
        result["decision_score"] += result["AST"] * 0.10
    if "TRB" in result.columns:
        result["decision_score"] += result["TRB"] * 0.08
    if "STL" in result.columns:
        result["decision_score"] += result["STL"] * 0.25
    if "BLK" in result.columns:
        result["decision_score"] += result["BLK"] * 0.30

    result["decision_flag"] = result["decision_score"].apply(
        lambda value: "watch" if value >= 20 else "baseline"
    )
    return result
