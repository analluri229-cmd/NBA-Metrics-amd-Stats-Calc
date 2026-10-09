"""Adapter for CSV output of ``basketball_reference_web_scraper``.

Raw files (written by ``extract.pull_season`` / ``extract.pull_box_scores`` or by
calling the library directly with ``output_type=OutputType.CSV``):

    data/raw/basketball_reference/<season>/players_season_totals.csv
    data/raw/basketball_reference/<season>/standings.csv
    data/raw/basketball_reference/<season>/season_schedule.csv
    data/raw/basketball_reference/<season>/player_box_scores_<YYYY-MM-DD>.csv
"""
from __future__ import annotations

import re
from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, read_csv_rows, to_float
from ...canonical.dates import eastern_game_date
from ...canonical.games import game_id, game_key
from ...canonical.resolver import IdResolver
from .player_season import compact_season_row

DATA_TYPES = ("players_season_totals", "standings", "season_schedule", "player_box_scores")
BOX_SCORE_FILE = re.compile(r"^player_box_scores_(\d{4}-\d{2}-\d{2})\.csv$")
HOME_AWAY = {"HOME": "H", "AWAY": "A"}


class WebScraperAdapter:
    source_name = "bbref_web"
    source_system = "basketball_reference"

    def discover(self, raw_root: Path) -> list[RawFile]:
        found = []
        for season_dir in sorted((raw_root / "basketball_reference").glob("[0-9][0-9][0-9][0-9]")):
            season = int(season_dir.name)
            for path in sorted(season_dir.glob("*.csv")):
                if path.stem in DATA_TYPES:
                    found.append(RawFile.from_path(path, self.source_name, path.stem, season))
                elif BOX_SCORE_FILE.match(path.name):
                    found.append(RawFile.from_path(path, self.source_name, "player_box_scores", season))
        return sorted(found, key=lambda r: (r.season, DATA_TYPES.index(r.data_type), r.path.name))

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        result = new_result(self, raw)
        rows = read_csv_rows(raw.path)
        result.raw_row_count = len(rows)
        parser = getattr(self, f"_parse_{raw.data_type}")
        for index, row in enumerate(rows):
            parser(raw, index, row, resolver, result)
        return result

    def _team(self, raw: RawFile, value: str, resolver: IdResolver) -> str | None:
        return resolver.team(self.source_name, value, {"file": raw.path.name})

    def _parse_players_season_totals(self, raw, index, row, resolver, result) -> None:
        team_id = self._team(raw, row.get("team", ""), resolver)
        slug = (row.get("slug") or "").strip()
        if not slug or team_id is None:
            result.skip(index, "missing slug or unknown team")
            return
        resolver.register_player(self.source_name, slug, row["name"], raw.season, team_id)
        result.add("dim_player", {"player_id": slug, "player_name": row["name"],
                                  "position": (row.get("positions") or "").title() or None})
        # The library drops combined rows, so every row here is one team stint.
        stats = {
            "games": to_float(row.get("games_played")), "games_started": to_float(row.get("games_started")),
            "mp": to_float(row.get("minutes_played")), "pts": to_float(row.get("points")),
            "trb": _sum(row.get("offensive_rebounds"), row.get("defensive_rebounds")),
            "ast": to_float(row.get("assists")), "fga": to_float(row.get("attempted_field_goals")),
            "fta": to_float(row.get("attempted_free_throws")),
        }
        result.add("fact_player_season", compact_season_row(raw.season, slug, team_id, stats))

    def _parse_standings(self, raw, index, row, resolver, result) -> None:
        team_id = self._team(raw, row.get("team", ""), resolver)
        if team_id is None:
            result.skip(index, "unknown team")
            return
        result.add("fact_team_season", {
            "team_season_id": f"{raw.season}_{team_id}", "team_id": team_id, "season": raw.season,
            "wins": to_float(row.get("wins")), "losses": to_float(row.get("losses")),
        })

    def _parse_season_schedule(self, raw, index, row, resolver, result) -> None:
        away = self._team(raw, row.get("away_team", ""), resolver)
        home = self._team(raw, row.get("home_team", ""), resolver)
        away_pts, home_pts = to_float(row.get("away_team_score")), to_float(row.get("home_team_score"))
        date_id = eastern_game_date(row.get("start_time", ""))
        if away is None or home is None or date_id is None:
            result.skip(index, "unknown team or date")
            return
        if away_pts is None or home_pts is None:
            result.skip(index, "not played yet")
            return
        gid = game_id(date_id, away, home)
        season = raw.season
        for team, opponent, side, pts_for, pts_against in (
            (home, away, "H", home_pts, away_pts), (away, home, "A", away_pts, home_pts)
        ):
            result.add("fact_team_game", {
                "team_game_id": f"{date_id}_{team}", "team_id": team, "opponent_team_id": opponent,
                "date_id": date_id, "season": season, "game_id": gid, "home_away": side,
                "points_for": pts_for, "points_against": pts_against,
            })

    def _parse_player_box_scores(self, raw, index, row, resolver, result) -> None:
        date_id = BOX_SCORE_FILE.match(raw.path.name)[1]
        team_id = self._team(raw, row.get("team", ""), resolver)
        opponent_id = self._team(raw, row.get("opponent", ""), resolver)
        slug = (row.get("slug") or "").strip()
        if not slug or team_id is None or opponent_id is None:
            result.skip(index, "missing slug or unknown team")
            return
        resolver.register_player(self.source_name, slug, row.get("name") or slug, raw.season, team_id)
        fgm, fg3m, ftm = (to_float(row.get(c)) for c in
                          ("made_field_goals", "made_three_point_field_goals", "made_free_throws"))
        seconds = to_float(row.get("seconds_played"))
        home_away = HOME_AWAY.get((row.get("location") or "").upper())
        result.add("fact_player_game", {
            "player_game_id": f"{date_id}_{slug}", "player_id": slug, "team_id": team_id,
            "date_id": date_id, "season": raw.season, "opponent_team_id": opponent_id,
            "game_id": game_key(date_id, team_id, opponent_id, home_away), "home_away": home_away,
            "minutes": round(seconds / 60, 2) if seconds is not None else None,
            "points": 2 * fgm + fg3m + ftm if None not in (fgm, fg3m, ftm) else None,
            "rebounds": _sum(row.get("offensive_rebounds"), row.get("defensive_rebounds")),
            "assists": to_float(row.get("assists")), "steals": to_float(row.get("steals")),
            "blocks": to_float(row.get("blocks")), "fgm": fgm, "fga": to_float(row.get("attempted_field_goals")),
            "fg3m": fg3m, "fg3a": to_float(row.get("attempted_three_point_field_goals")), "ftm": ftm,
            "fta": to_float(row.get("attempted_free_throws")), "oreb": to_float(row.get("offensive_rebounds")),
            "dreb": to_float(row.get("defensive_rebounds")), "tov": to_float(row.get("turnovers")),
            "pf": to_float(row.get("personal_fouls")), "plus_minus": to_float(row.get("plus_minus")),
        })


def _sum(*values: object) -> float | None:
    numbers = [to_float(v) for v in values]
    return None if any(n is None for n in numbers) else sum(numbers)
