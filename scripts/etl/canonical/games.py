"""Canonical game identifiers, derived the same way for every source."""
from __future__ import annotations


def game_id(date_id: str, away_team_id: str, home_team_id: str) -> str:
    return f"{date_id}_{away_team_id}@{home_team_id}"


def game_key(date_id: str, team_id: str, opponent_id: str, home_away: str | None) -> str | None:
    """game_id seen from one team's side ('H' or 'A')."""
    if home_away == "H":
        return game_id(date_id, opponent_id, team_id)
    if home_away == "A":
        return game_id(date_id, team_id, opponent_id)
    return None
