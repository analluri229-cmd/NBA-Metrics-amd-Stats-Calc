from __future__ import annotations

import re
from typing import Iterable

from .canonical.dates import season_from_date


def canonicalize_team_name(team_name: str | None) -> str:
    if not team_name:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", team_name).strip()
    return cleaned.upper()


def canonicalize_player_name(player_name: str | None) -> str:
    if not player_name:
        return ""
    return re.sub(r"\s+", " ", player_name).strip()


def infer_season_from_date(date_value: str | None) -> int | None:
    """Season end year: 2025-11-01 -> 2026, 2026-04-01 -> 2026."""
    return season_from_date(date_value)


def normalize_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    if "team" in normalized:
        normalized["team"] = canonicalize_team_name(str(normalized["team"]))
    if "player" in normalized:
        normalized["player"] = canonicalize_player_name(str(normalized["player"]))
    if "date" in normalized:
        normalized["season"] = infer_season_from_date(str(normalized["date"]))
    return normalized


def normalize_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [normalize_row(row) for row in rows]
