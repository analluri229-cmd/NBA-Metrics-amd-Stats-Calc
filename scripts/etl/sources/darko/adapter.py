"""Adapter for DARKO snapshots saved by ``extract.pull_dates``.

Raw files: data/raw/darko/<season>/dpm_<data date>.json

Each file is the league as of one date. Every numeric column becomes a row of
``fact_player_rating_daily`` keyed by the snapshot's data date. DARKO identifies
players by NBA person id, the same key stats.nba.com uses, so players are resolved
in the nba_stats namespace and reuse its matches and overrides.
"""
from __future__ import annotations

from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, to_float
from ...canonical.dates import to_date_id
from ...canonical.resolver import IdResolver
from .page_data import page_data, player_rows

STAT_TABLE = "dpm"
# Player identity, and columns that compare the snapshot with today's ratings
# (now_dpm, since_dpm): they would leak later information into a dated row.
IDENTITY_COLUMNS = {"nba_id", "player_name", "team_name", "tm_id", "position", "season", "_rank",
                    "now_dpm", "since_dpm"}
PLAYER_KEY_SOURCE = "nba_stats"


class DarkoAdapter:
    source_name = "darko"
    source_system = "darko"

    def discover(self, raw_root: Path) -> list[RawFile]:
        return [
            RawFile.from_path(path, self.source_name, STAT_TABLE, int(season_dir.name))
            for season_dir in sorted((raw_root / "darko").glob("[0-9][0-9][0-9][0-9]"))
            for path in sorted(season_dir.glob("dpm_*.json"))
        ]

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        result = new_result(self, raw)
        data = page_data(raw.path.read_bytes())
        as_of = data.get("asOf") or {}
        date_id = to_date_id(as_of.get("dataDate"))
        season = int(as_of.get("season") or raw.season)
        records = player_rows(data)
        result.raw_row_count = len(records)
        if date_id is None:
            raise ValueError(f"{raw.path.name}: snapshot has no data date")

        for index, rec in enumerate(records):
            if not rec.get("nba_id"):
                result.skip(index, "no NBA person id")
                continue
            team_id = resolver.team(self.source_name, rec.get("team_name"), {"file": raw.path.name})
            person_id = str(int(rec["nba_id"]))
            player_id = resolver.player(PLAYER_KEY_SOURCE, person_id, rec.get("player_name") or "", team_id,
                                        season, fallback_id=f"nba_{person_id}")
            for stat_name, value in rec.items():
                number = None if stat_name in IDENTITY_COLUMNS else to_float(value)
                if number is not None:
                    result.add("fact_player_rating_daily", {
                        "date_id": date_id, "season": season, "player_id": player_id, "team_id": team_id,
                        "stat_table": STAT_TABLE, "stat_name": stat_name, "value": number,
                    })
        return result
