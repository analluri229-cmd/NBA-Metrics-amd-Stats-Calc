"""Registry of source adapters and the offline ingestion runner.

Adapters run in this order so canonical player ids (Basketball-Reference slugs)
exist before other sources are matched against them.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..canonical.contract import SourceAdapter
from ..canonical.loader import already_loaded, drop_unreferenced_fallback_players, ingest_file
from ..canonical.resolver import IdResolver
from ..paths import RAW_DIR
from .basketball_reference.player_season import PlayerSeasonAdapter
from .basketball_reference.team_season import TeamSeasonAdapter
from .basketball_reference.web_scraper import WebScraperAdapter
from .darko.adapter import DarkoAdapter
from .legacy.sample import LegacySampleAdapter
from .nba_stats.adapter import NbaStatsAdapter

ADAPTERS: dict[str, SourceAdapter] = {
    adapter.source_name: adapter
    for adapter in (
        TeamSeasonAdapter(),
        PlayerSeasonAdapter(),
        WebScraperAdapter(),
        NbaStatsAdapter(),
        DarkoAdapter(),  # after nba_stats: reuses its NBA person id matches
        LegacySampleAdapter(),
    )
}

# Shorthands accepted by the CLI.
SOURCE_GROUPS = {
    "bbref": ("bbref_team_season", "bbref_player_season", "bbref_web"),
    "basketball_reference": ("bbref_team_season", "bbref_player_season", "bbref_web"),
}


def resolve_sources(sources: list[str] | None) -> list[str]:
    if not sources:
        return list(ADAPTERS)
    names: list[str] = []
    for source in sources:
        for name in SOURCE_GROUPS.get(source, (source,)):
            if name not in ADAPTERS:
                raise ValueError(f"unknown source {name!r}; choose from {sorted([*ADAPTERS, *SOURCE_GROUPS])}")
            if name not in names:
                names.append(name)
    return [name for name in ADAPTERS if name in names]


def ingest(conn: sqlite3.Connection, sources: list[str] | None = None, season: int | None = None,
           force: bool = False, raw_root: Path = RAW_DIR) -> list[dict]:
    work = [
        (ADAPTERS[name], raw)
        for name in resolve_sources(sources)
        for raw in ADAPTERS[name].discover(raw_root)
        if season is None or raw.season in (season, None)
    ]
    # One resolver for the whole run: building it reads the entire warehouse.
    pending = any(force or not already_loaded(conn, raw) for _, raw in work)
    resolver = IdResolver.from_connection(conn) if pending else None
    summaries = [ingest_file(conn, adapter, raw, force=force, resolver=resolver) for adapter, raw in work]
    if resolver is not None:
        drop_unreferenced_fallback_players(conn)
    return summaries


def rows_by_source(summaries: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for summary in summaries:
        totals[summary["source_name"]] = totals.get(summary["source_name"], 0) + summary.get("rows_inserted", 0) \
            + summary.get("rows_updated", 0)
    return totals
