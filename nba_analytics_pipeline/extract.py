from __future__ import annotations

from typing import Iterable, List, Optional

import pandas as pd

from basketball_reference_scraper.players import get_stats
from basketball_reference_scraper.teams import get_team_stats


def extract_player_snapshot(
    player_names: Optional[Iterable[str]] = None,
    season_end_year: int = 2025,
    stat_type: str = "PER_GAME",
) -> pd.DataFrame:
    """Extract player season-level data for a given list of players."""
    names = list(player_names or [])
    if not names:
        return pd.DataFrame()

    frames = []
    for player_name in names:
        try:
            df = get_stats(player_name, stat_type=stat_type, playoffs=False, career=False)
            if df.empty:
                continue
            df["player_name"] = player_name
            df["season_end_year"] = season_end_year
            frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def extract_team_snapshot(
    team_names: Optional[Iterable[str]] = None,
    season_end_year: int = 2025,
    data_format: str = "PER_GAME",
) -> pd.DataFrame:
    """Extract team-level performance data for a list of teams."""
    names = list(team_names or [])
    if not names:
        return pd.DataFrame()

    rows = []
    for team in names:
        try:
            series = get_team_stats(team, season_end_year, data_format=data_format)
            if series.empty:
                continue
            row = series.to_dict()
            row["team"] = team
            row["season_end_year"] = season_end_year
            rows.append(row)
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
