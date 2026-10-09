"""Adapter for the team/opponent season tables written by ``pull --source bbref_team`` (``team_extract.py``).

Raw files: data/raw/{team,opponent}_{totals,per_100_poss}_<season>.csv
"""
from __future__ import annotations

import re
from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, read_csv_rows, to_bool, to_float
from ...canonical.resolver import IdResolver

FILE_PATTERN = re.compile(r"^(team|opponent)_(totals|per_100_poss)_(\d{4})\.csv$")

BOX_COLUMNS = {
    "G": "g", "MP": "mp", "FG": "fg", "FGA": "fga", "FG%": "fg_pct", "3P": "fg3", "3PA": "fg3a",
    "3P%": "fg3_pct", "2P": "fg2", "2PA": "fg2a", "2P%": "fg2_pct", "FT": "ft", "FTA": "fta", "FT%": "ft_pct",
    "ORB": "orb", "DRB": "drb", "TRB": "trb", "AST": "ast", "STL": "stl", "BLK": "blk", "TOV": "tov",
    "PF": "pf", "PTS": "pts",
}


class TeamSeasonAdapter:
    source_name = "bbref_team_season"
    source_system = "basketball_reference"

    def discover(self, raw_root: Path) -> list[RawFile]:
        found = []
        for path in sorted(raw_root.glob("*.csv")):
            match = FILE_PATTERN.match(path.name)
            if match:
                data_type = f"{match[1]}_{match[2]}"
                found.append(RawFile.from_path(path, self.source_name, data_type, int(match[3])))
        return sorted(found, key=lambda r: (r.season, r.data_type))

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        result = new_result(self, raw)
        perspective, stat_basis = raw.data_type.split("_", 1)
        rows = read_csv_rows(raw.path)
        result.raw_row_count = len(rows)

        for index, row in enumerate(rows):
            team_name = (row.get("Team") or "").strip()
            if not team_name or team_name in ("Team", "League Average"):
                result.skip(index, "not a team row")
                continue
            team_id = resolver.team(self.source_name, team_name, {"file": raw.path.name})
            if team_id is None:
                result.skip(index, f"unknown team {team_name!r}")
                continue
            season = int(to_float(row.get("Season")) or raw.season)

            box = {canonical: to_float(row.get(column)) for column, canonical in BOX_COLUMNS.items()}
            result.add("fact_team_season_box", {
                "team_season_box_id": f"{season}_{team_id}_{perspective}_{stat_basis}",
                "team_id": team_id, "season": season, "perspective": perspective, "stat_basis": stat_basis,
                **box,
            })

            team_season = {"team_season_id": f"{season}_{team_id}", "team_id": team_id, "season": season}
            playoffs = to_bool(row.get("Playoffs"))
            if playoffs is not None:
                team_season["playoff_appearance"] = int(playoffs)
            # Points per 100 possessions is the offensive (team) / defensive (opponent) rating.
            if stat_basis == "per_100_poss":
                team_season["off_rtg" if perspective == "team" else "def_rtg"] = box["pts"]
            result.add("fact_team_season", team_season)
        return result
