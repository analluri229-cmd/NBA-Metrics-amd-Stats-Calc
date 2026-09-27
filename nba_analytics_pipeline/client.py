from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from .config import DEFAULT_PLAYERS, DEFAULT_SEASON, DEFAULT_TEAMS
from .extract import extract_player_snapshot, extract_team_snapshot
from .load import save_dataframe, save_tableau_ready
from .transform import build_player_snapshot, build_team_snapshot


def run_pipeline(
    season_end_year: int = DEFAULT_SEASON,
    player_names: Optional[Iterable[str]] = None,
    team_names: Optional[Iterable[str]] = None,
) -> dict[str, pd.DataFrame]:
    """Run the end-to-end ETL and export normalized outputs."""
    player_names = list(player_names or DEFAULT_PLAYERS)
    team_names = list(team_names or DEFAULT_TEAMS)

    player_raw = extract_player_snapshot(player_names, season_end_year=season_end_year)
    team_raw = extract_team_snapshot(team_names, season_end_year=season_end_year)

    player_snapshot = build_player_snapshot(player_raw)
    team_snapshot = build_team_snapshot(team_raw)

    save_dataframe(player_snapshot, "player_snapshot.csv")
    save_dataframe(team_snapshot, "team_snapshot.csv")
    save_tableau_ready(player_snapshot, "player_snapshot_tableau.csv")
    save_tableau_ready(team_snapshot, "team_snapshot_tableau.csv")

    return {
        "player_raw": player_raw,
        "team_raw": team_raw,
        "player_snapshot": player_snapshot,
        "team_snapshot": team_snapshot,
    }
