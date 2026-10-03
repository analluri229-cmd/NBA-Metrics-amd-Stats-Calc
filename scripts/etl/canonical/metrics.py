"""Derived metrics computed the same way for every source."""
from __future__ import annotations


def true_shooting(points: float | None, fga: float | None, fta: float | None) -> float | None:
    if points is None or fga is None:
        return None
    denominator = 2 * (fga + 0.44 * (fta or 0))
    return round(points / denominator, 4) if denominator > 0 else None


def possessions_used_per_minute(
    fga: float | None, fta: float | None, tov: float | None, minutes: float | None
) -> float | None:
    """Usage proxy: shots, trips to the line and turnovers per minute played."""
    if fga is None or not minutes:
        return None
    return round((fga + 0.44 * (fta or 0) + (tov or 0)) / minutes, 4)


def team_possessions(fga: float, fta: float, oreb: float, tov: float) -> float:
    return fga + 0.44 * fta - oreb + tov


def per_game(total: float | None, games: float | None) -> float | None:
    if total is None or not games:
        return None
    return round(total / games, 1)
