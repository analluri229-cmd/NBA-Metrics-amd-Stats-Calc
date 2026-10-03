"""Adapter for Basketball-Reference league player stat pages.

Raw files: data/raw/basketball_reference/<season>/player_<stat_table>.html, saved
unmodified by ``extract.pull_player_tables``. Each page holds a regular-season
table and a playoffs table (id ending in ``_post``).

Traded players have a combined row (team ``2TM``/``3TM``/``TOT``) plus one row
per team. The combined row becomes split ``TOT``; team rows keep the team as
the split. A player with a single team row gets split ``TOT`` and that team_id.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, to_float
from ...canonical.metrics import per_game, true_shooting
from ...canonical.resolver import IdResolver
from ...canonical.schema import FULL_SEASON_SPLIT
from .html_tables import Row, read_tables

# canonical stat_table -> Basketball-Reference page suffix (NBA_<season>_<suffix>.html)
PLAYER_PAGES = {
    "totals": "totals",
    "per_game": "per_game",
    "per_36": "per_minute",
    "per_100": "per_poss",
    "advanced": "advanced",
    "play_by_play": "play-by-play",
    "shooting": "shooting",
    "adj_shooting": "adj_shooting",
}

IDENTITY_STATS = {"ranker", "name_display", "player", "team_name_abbr", "team_id", "pos", "awards", ""}
COMBINED_TEAM = re.compile(r"^(TOT|\d+TM)$")
FILE_PATTERN = re.compile(r"^player_([a-z_0-9]+)\.html$")


def cell_value(csk: str | None, text: str) -> float | None:
    """Prefer the full-precision sort key; fall back to the displayed text."""
    value = to_float(csk) if csk is not None else None
    return value if value is not None else to_float(text)


class PlayerSeasonAdapter:
    source_name = "bbref_player_season"
    source_system = "basketball_reference"

    def discover(self, raw_root: Path) -> list[RawFile]:
        found = []
        for season_dir in sorted((raw_root / "basketball_reference").glob("[0-9][0-9][0-9][0-9]")):
            for path in sorted(season_dir.glob("player_*.html")):
                match = FILE_PATTERN.match(path.name)
                if match and match[1] in PLAYER_PAGES:
                    found.append(RawFile.from_path(path, self.source_name, match[1], int(season_dir.name)))
        order = list(PLAYER_PAGES)
        return sorted(found, key=lambda r: (r.season, order.index(r.data_type)))

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        result = new_result(self, raw)
        tables = read_tables(raw.path.read_text(encoding="utf-8"))
        for table_id, rows in tables.items():
            player_rows = [row for row in rows if row.slug and "thead" not in row.css_class]
            if not player_rows:
                continue
            season_type = "playoffs" if table_id.endswith("_post") else "regular"
            result.raw_row_count += len(player_rows)
            self._parse_table(raw, season_type, player_rows, resolver, result)
        if result.raw_row_count == 0:
            raise ValueError(f"no player rows found in {raw.path.name}")
        return result

    def _parse_table(self, raw: RawFile, season_type: str, rows: list[Row], resolver: IdResolver,
                     result: AdapterResult) -> None:
        season = raw.season
        traded = {row.slug for row in rows if COMBINED_TEAM.match(row.text("team_name_abbr") or "")}

        for index, row in enumerate(rows):
            slug = row.slug
            name = row.text("name_display") or row.text("player") or slug
            team_code = row.text("team_name_abbr") or row.text("team_id") or ""
            if COMBINED_TEAM.match(team_code):
                split, team_id = FULL_SEASON_SPLIT, None
            else:
                team_id = resolver.team(self.source_name, team_code, {"file": raw.path.name, "player": slug})
                if team_id is None:
                    result.skip(index, f"unknown team {team_code!r} for {slug}")
                    continue
                split = team_id if slug in traded else FULL_SEASON_SPLIT

            resolver.register_player(self.source_name, slug, name, season, team_id)
            if season_type == "regular":
                player = {"player_id": slug, "player_name": name, "position": row.text("pos") or None}
                if slug not in traded:
                    player["team_id_current"] = team_id
                result.add("dim_player", player)

            stats: dict[str, float] = {}
            for cell in row.cells:
                if cell.stat in IDENTITY_STATS:
                    continue
                value = cell_value(cell.csk, cell.text)
                if value is None:
                    continue
                stat_name = cell.stat
                suffix = 2
                while stat_name in stats:
                    stat_name, suffix = f"{cell.stat}_{suffix}", suffix + 1
                stats[stat_name] = value

            for stat_name, value in stats.items():
                result.add("fact_player_season_stat", {
                    "season": season, "season_type": season_type, "player_id": slug, "split": split,
                    "stat_table": raw.data_type, "stat_name": stat_name, "value": value, "team_id": team_id,
                })

            if raw.data_type == "totals" and season_type == "regular":
                result.add("fact_player_season", compact_season_row(season, slug, split, stats))


def compact_season_row(season: int, player_id: str, split: str, stats: dict[str, float]) -> dict:
    games = stats.get("games", stats.get("g"))
    points, rebounds, assists = stats.get("pts"), stats.get("trb"), stats.get("ast")
    return {
        "player_season_id": f"{season}_{player_id}_{split}", "player_id": player_id, "season": season,
        "team_id": split, "games": games, "games_started": stats.get("games_started", stats.get("gs")),
        "minutes": stats.get("mp"), "points": points, "rebounds": rebounds, "assists": assists,
        "ppg": per_game(points, games), "rpg": per_game(rebounds, games), "apg": per_game(assists, games),
        "efficiency_rating": true_shooting(points, stats.get("fga"), stats.get("fta")),
    }
