"""Adapter for the hand-made sample files the demo pipeline started with.

Raw files:
    data/raw/historical/*.csv   player_name, team_name, date, minutes, points, ...
    data/raw/nba_stats/*.json   list of the same fields (top level of nba_stats/ only)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, read_csv_rows, to_float
from ...canonical.dates import season_from_date, to_date_id
from ...canonical.players import name_slug, normalize_name
from ...canonical.resolver import IdResolver

REQUIRED = {"player_name", "team_name", "date"}


class LegacySampleAdapter:
    source_name = "legacy_sample"
    source_system = "legacy_sample"

    def discover(self, raw_root: Path) -> list[RawFile]:
        found = []
        for path in sorted((raw_root / "historical").glob("*.csv")):
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                header = next(csv.reader(handle), [])
            if REQUIRED <= set(header):
                found.append(RawFile.from_path(path, self.source_name, "player_game_csv", None))
        for path in sorted((raw_root / "nba_stats").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list) and payload and REQUIRED <= set(payload[0]):
                found.append(RawFile.from_path(path, self.source_name, "player_game_json", None))
        return found

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        result = new_result(self, raw)
        if raw.data_type == "player_game_csv":
            rows = read_csv_rows(raw.path)
        else:
            rows = json.loads(raw.path.read_text(encoding="utf-8"))
        result.raw_row_count = len(rows)

        for index, row in enumerate(rows):
            date_id = to_date_id(row.get("date"))
            team_id = resolver.team(self.source_name, row.get("team_name"), {"file": raw.path.name})
            if date_id is None or team_id is None:
                result.skip(index, "unknown team or date")
                continue
            season = season_from_date(date_id)
            name = str(row["player_name"])
            player_id = resolver.player(self.source_name, normalize_name(name), name, team_id, season,
                                        fallback_id=name_slug(name))
            result.add("fact_player_game", {
                "player_game_id": f"{date_id}_{player_id}", "player_id": player_id, "team_id": team_id,
                "date_id": date_id, "season": season,
                **{col: to_float(row.get(col)) for col in
                   ("minutes", "points", "rebounds", "assists", "steals", "blocks")},
            })
        return result
