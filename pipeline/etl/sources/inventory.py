"""What a source already has on disk for a season, so a pull can skip, fill gaps or start fresh.

Counts use the same path helpers the extractors write with, so they can't drift apart.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pipeline import settings

from ..canonical.teams import FRANCHISES
from .basketball_reference.player_season import PLAYER_PAGES
from .basketball_reference.team_extract import TABLES as TEAM_TABLES
from .nba_stats.extract import ALL_TABLES, TEAM_REQUEST_TABLES, raw_path, team_raw_path


@dataclass(frozen=True)
class Inventory:
    source: str
    season: int
    have: int
    expected: int | None  # None: no fixed count (DARKO snapshots)

    @property
    def status(self) -> Literal["none", "partial", "all"]:
        if self.have == 0:
            return "none"
        if self.expected is not None and self.have >= self.expected:
            return "all"
        return "partial"


def _season_types(season_type: str) -> list[str]:
    return ["regular", "playoffs"] if season_type == "both" else [season_type]


def inventory(source: str, season: int, season_type: str = "regular", raw_root: Path | None = None) -> Inventory:
    """Files on disk for ``source`` and ``season``; ``season_type`` matters for nba_stats only."""
    raw_root = Path(raw_root or settings.RAW_DIR)
    if source == "nba_stats":
        out = raw_root / "nba_stats"
        teams = [f.team_id for f in FRANCHISES]
        paths = [raw_path(season, table, st, out) for st in _season_types(season_type) for table in ALL_TABLES]
        paths += [team_raw_path(season, table, team, st, out)
                  for st in _season_types(season_type) for table in TEAM_REQUEST_TABLES for team in teams]
        return Inventory(source, season, sum(p.exists() for p in paths), len(paths))
    if source == "bbref":
        folder = raw_root / "basketball_reference" / str(season)
        have = sum((folder / f"player_{table}.html").exists() for table in PLAYER_PAGES)
        return Inventory(source, season, have, len(PLAYER_PAGES))
    if source == "bbref_team":
        have = sum((raw_root / f"{stem}_{season}.csv").exists() for stem in TEAM_TABLES.values())
        return Inventory(source, season, have, len(TEAM_TABLES))
    if source == "darko":
        return Inventory(source, season, len(list((raw_root / "darko" / str(season)).glob("dpm_*.json"))), None)
    raise ValueError(f"unknown source {source!r}; allowed: {', '.join(settings.SOURCE_CHOICES)}")
