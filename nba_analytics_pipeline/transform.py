from __future__ import annotations

from typing import Iterable

import pandas as pd

from .metrics import add_decision_metrics


def normalize_player_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize player output to a Tableau-ready schema."""
    if df.empty:
        return df

    result = df.copy()
    result.columns = [str(col).upper().replace("%", "PCT") for col in result.columns]
    result["source"] = "basketball_reference"
    return result


def normalize_team_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize team output to a Tableau-ready schema."""
    if df.empty:
        return df

    result = df.copy()
    result.columns = [str(col).upper().replace("%", "PCT") for col in result.columns]
    result["source"] = "basketball_reference"
    return result


def build_player_snapshot(player_df: pd.DataFrame) -> pd.DataFrame:
    if player_df.empty:
        return player_df
    player_df = normalize_player_data(player_df)
    return add_decision_metrics(player_df)


def build_team_snapshot(team_df: pd.DataFrame) -> pd.DataFrame:
    if team_df.empty:
        return team_df
    team_df = normalize_team_data(team_df)
    return add_decision_metrics(team_df)
