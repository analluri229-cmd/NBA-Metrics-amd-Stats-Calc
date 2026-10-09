"""Adapter for stats.nba.com JSON saved by ``extract.pull_season``.

Raw files: data/raw/nba_stats/<season>/<data_type>[_playoffs].json

LeagueDash, tracking, hustle, clutch and defense tables are full-season lines
across all teams, so they are stored with split ``TOT`` and team_id = the
player's latest team. Play types list traded players per team; those rows keep
the team as the split and a combined ``TOT`` row is rebuilt (see
``combine_play_type_stints``). ``player_bio`` fills dim_player (height in
inches, weight in lb, draft, college, country).

Per-team files (data/raw/nba_stats/<season>/<table>/<TEAM>.json):
- ``shot_chart``: one fact_shot row per field goal attempt.
- ``on_off``: the team's box score with each player on and off the court, as stat table
  ``on_off`` (``on_fg3a``, ``off_fg3a``...). On/off is per team, so the split is the team.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, to_float
from ...canonical.dates import to_date_id
from ...canonical.games import game_key
from ...canonical.metrics import per_game, team_possessions, true_shooting
from ...canonical.resolver import IdResolver
from ...canonical.schema import FULL_SEASON_SPLIT
from .extract import (GAME_LOGS, LINEUP_TABLES, PLAYER_BIO, PLAYER_SEASON_TABLES, TEAM_REQUEST_TABLES,
                      TEAM_SEASON_TABLES, TEAM_TABLES)

DATA_TYPES = (*TEAM_TABLES, *TEAM_SEASON_TABLES, *PLAYER_BIO, *PLAYER_SEASON_TABLES, *GAME_LOGS, *LINEUP_TABLES,
              *TEAM_REQUEST_TABLES)
IDENTITY_COLUMNS = {"player_id", "player_name", "nickname", "team_id", "team_abbreviation", "team_name",
                    "team_count", "cfid", "cfparams", "wnba_fantasy_pts",
                    # defense tables name the player/team columns differently
                    "close_def_person_id", "player_last_team_id", "player_last_team_abbreviation", "player_position",
                    # text labels on play type and clutch rows
                    "season_id", "play_type", "type_grouping", "group_set",
                    # lineup identity and an internal timing column
                    "group_id", "group_name", "sum_time_played",
                    # on/off: the player the row is about
                    "vs_player_id", "vs_player_name", "court_status", "group_value"}
# stats.nba.com sort helpers that duplicate other columns (sp_work_off_rating == off_rating, ...).
SKIP_PREFIXES = ("sp_work_",)
# Every tracking table repeats the team's season record; every shot context table repeats games and age.
TRACKING_REDUNDANT = {"w", "l", "w_pct"}
SHOT_CONTEXT_REDUNDANT = {"gp", "g", "age"}
MATCHUP = re.compile(r"^\s*(\w+)\s+(vs\.|@)\s+(\w+)\s*$")

# Play type files (one per play type and side) share a stat table per side,
# with the play type as the stat name prefix: play_type_offense / isolation_ppp.
PLAY_TYPE_FILE = re.compile(r"^(?:player|team)_season_play_type_(?P<play_type>.+)_(?P<side>offense|defense)$")
# Defender distance x shot clock files share one stat table, with the pair as the stat name prefix:
# shot_context / very_tight_clock_4_0_fga.
SHOT_CONTEXT_FILE = re.compile(r"^player_season_shot_context_(?P<bin>.+)$")
# Team base/advanced files keep their original names; their stat tables match the player ones.
STAT_TABLE_NAMES = {"team_season_stats": "totals", "team_season_advanced": "advanced"}
# Play types list traded players once per team. The full-season line is rebuilt
# exactly: counts are summed, possession shares weighted by possessions and
# shooting percentages by attempts. Synergy percentile and poss_pct cannot be
# recombined and are left out of the TOT row.
PLAY_TYPE_SUMS = ("gp", "poss", "pts", "fgm", "fga", "fgmx")
PLAY_TYPE_PER_POSS = ("ft_poss_pct", "tov_poss_pct", "sf_poss_pct", "plusone_poss_pct", "score_poss_pct")
PLAY_TYPE_PER_FGA = ("fg_pct", "efg_pct")


def stat_table_for(data_type: str) -> tuple[str, str]:
    """(stat_table, stat_name prefix) for a player or team season data type."""
    match = PLAY_TYPE_FILE.match(data_type)
    if match:
        return f"play_type_{match['side']}", f"{match['play_type']}_"
    if match := SHOT_CONTEXT_FILE.match(data_type):
        return "shot_context", f"{match['bin']}_"
    if data_type in STAT_TABLE_NAMES:
        return STAT_TABLE_NAMES[data_type], ""
    return data_type.removeprefix("player_season_").removeprefix("team_season_"), ""


def numeric_stats(rec: dict, stat_table: str) -> dict[str, float]:
    """The numeric stat columns of a row, without identity, rank and duplicate columns."""
    stats = {}
    for column, value in rec.items():
        if column in IDENTITY_COLUMNS or column.endswith("_rank") or column.startswith(SKIP_PREFIXES):
            continue
        if stat_table.startswith("tracking_") and column in TRACKING_REDUNDANT:
            continue
        if stat_table == "shot_context" and column in SHOT_CONTEXT_REDUNDANT:
            continue
        number = to_float(value)
        if number is not None:
            stats[column] = number
    return stats


def combine_play_type_stints(stints: list[dict[str, float]]) -> dict[str, float]:
    total: dict[str, float | None] = {k: sum(s.get(k) or 0 for s in stints) for k in PLAY_TYPE_SUMS}
    poss, fga = total["poss"], total["fga"]
    for key in PLAY_TYPE_PER_POSS:
        total[key] = round(sum((s.get(key) or 0) * (s.get("poss") or 0) for s in stints) / poss, 3) if poss else None
    for key in PLAY_TYPE_PER_FGA:
        total[key] = round(sum((s.get(key) or 0) * (s.get("fga") or 0) for s in stints) / fga, 3) if fga else None
    total["ppp"] = round(total["pts"] / poss, 3) if poss else None
    return {k: v for k, v in total.items() if v is not None}


# Closest-defender tables sometimes list a player twice in one season (split by the
# position listed at the time). (made, attempted, pct, normal pct, pct vs normal) per table.
DEFENSE_SHOTS = {
    "defense_overall": ("d_fgm", "d_fga", "d_fg_pct", "normal_fg_pct", "pct_plusminus"),
    "defense_3pt": ("fg3m", "fg3a", "fg3_pct", "ns_fg3_pct", "plusminus"),
    "defense_rim": ("fgm_lt_06", "fga_lt_06", "lt_06_pct", "ns_lt_06_pct", "plusminus"),
}


def combine_defense_stints(stat_table: str, stints: list[dict[str, float]]) -> dict[str, float]:
    made, attempted, pct, normal, vs_normal = DEFENSE_SHOTS[stat_table]
    fga = sum(s.get(attempted) or 0 for s in stints)
    total = {k: sum(s.get(k) or 0 for s in stints) for k in ("gp", "g", made, attempted)}
    total["age"] = max(s.get("age") or 0 for s in stints)
    if fga:
        total[pct] = round(total[made] / fga, 3)
        total[normal] = round(sum((s.get(normal) or 0) * (s.get(attempted) or 0) for s in stints) / fga, 3)
        total[vs_normal] = round(total[pct] - total[normal], 3)
    # freq = this category's share of all shots defended; recover each stint's total from fga / freq.
    all_shots = sum((s.get(attempted) or 0) / s["freq"] for s in stints if s.get("freq"))
    if all_shots:
        total["freq"] = round(fga / all_shots, 3)
    return total


def _int(value: object) -> int | None:
    number = to_float(value)
    return int(number) if number is not None else None


def _text(value: object) -> str | None:
    text = str(value or "").strip()
    return None if text in ("", "None", "Undrafted") else text


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def result_sets(payload: dict) -> dict[str, tuple[list[str], list[list]]]:
    """Every result set by name: (lower-case column names, rows)."""
    sets = payload.get("resultSets", payload.get("resultSet"))
    sets = sets if isinstance(sets, list) else [sets]
    return {rs["name"]: ([h.lower() for h in rs["headers"]], rs["rowSet"]) for rs in sets}


def _first_last(name: str) -> str:
    """'Banchero, Paolo' -> 'Paolo Banchero' (on/off lists players as last, first)."""
    last, _, first = str(name or "").partition(", ")
    return f"{first} {last}" if first else last


def result_table(payload: dict) -> tuple[list[str], list[list]]:
    """Return (flat column names, rows) for the first result set.

    Shot-location endpoints use two header levels (category x FGM/FGA/FG_PCT);
    those become e.g. ``restricted_area_fga``.
    """
    sets = payload.get("resultSets", payload.get("resultSet"))
    result = sets[0] if isinstance(sets, list) else sets
    headers = result["headers"]
    if headers and isinstance(headers[0], dict):
        categories = next(h for h in headers if h["name"] != "columns")
        columns = next(h for h in headers if h["name"] == "columns")["columnNames"]
        skip, span = categories.get("columnsToSkip", 0), categories["columnSpan"]
        names = [c.lower() for c in columns[:skip]]
        for i, column in enumerate(columns[skip:]):
            names.append(f"{_slug(categories['columnNames'][i // span])}_{column.lower()}")
        return names, result["rowSet"]
    return [h.lower() for h in headers], result["rowSet"]


class NbaStatsAdapter:
    source_name = "nba_stats"
    source_system = "nba_stats"

    def discover(self, raw_root: Path) -> list[RawFile]:
        found = []
        for season_dir in sorted((raw_root / "nba_stats").glob("[0-9][0-9][0-9][0-9]")):
            for path in sorted(season_dir.glob("*.json")):
                base = path.stem.removesuffix("_playoffs")
                if base in DATA_TYPES:
                    found.append(RawFile.from_path(path, self.source_name, path.stem, int(season_dir.name)))
            for table in TEAM_REQUEST_TABLES:
                for path in sorted((season_dir / table).glob("*.json")):
                    data_type = f"{table}_playoffs" if path.stem.endswith("_playoffs") else table
                    found.append(RawFile.from_path(path, self.source_name, data_type, int(season_dir.name)))
        return sorted(found, key=lambda r: (r.season, r.data_type.endswith("_playoffs"),
                                            DATA_TYPES.index(r.data_type.removesuffix("_playoffs"))))

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        result = new_result(self, raw)
        payload = json.loads(raw.path.read_text(encoding="utf-8"))
        season_type = "playoffs" if raw.data_type.endswith("_playoffs") else "regular"
        base = raw.data_type.removesuffix("_playoffs")
        if base == "on_off":
            self._on_off(raw, season_type, payload, resolver, result)
            return result
        columns, rows = result_table(payload)
        records = [dict(zip(columns, row)) for row in rows]
        result.raw_row_count = len(records)

        if base in PLAYER_SEASON_TABLES:
            self._player_season(raw, base, season_type, records, resolver, result)
        elif base in PLAYER_BIO:
            self._player_bio(raw, season_type, records, resolver, result)
        elif base in TEAM_TABLES:
            self._team_season(raw, season_type, records, resolver, result)
            self._team_stats(raw, base, season_type, records, resolver, result)
        elif base in TEAM_SEASON_TABLES:
            self._team_stats(raw, base, season_type, records, resolver, result)
        elif base in LINEUP_TABLES:
            self._lineups(raw, base, season_type, records, resolver, result)
        elif base == "player_game_log":
            self._player_games(raw, season_type, records, resolver, result)
        elif base == "team_game_log":
            self._team_games(raw, season_type, records, resolver, result)
        elif base == "shot_chart":
            self._shots(raw, season_type, records, resolver, result)
        return result

    def _shots(self, raw, season_type, records, resolver, result) -> None:
        context = {"file": f"{raw.path.parent.name}/{raw.path.name}"}
        for index, rec in enumerate(records):
            text = str(rec.get("game_date") or "")
            date_id = to_date_id(f"{text[:4]}-{text[4:6]}-{text[6:8]}") if len(text) == 8 else None
            team_id = resolver.team(self.source_name, rec.get("team_name"), context)
            home_id = resolver.team(self.source_name, rec.get("htm"), context)
            away_id = resolver.team(self.source_name, rec.get("vtm"), context)
            if date_id is None or team_id is None or team_id not in (home_id, away_id):
                result.skip(index, "unknown date or team")
                continue
            home_away = "H" if team_id == home_id else "A"
            opponent_id = away_id if home_away == "H" else home_id
            player_id = self._player(raw, rec, team_id, resolver, raw.season)
            self._playoff_date(date_id, raw.season, season_type, result)
            result.add("fact_shot", {
                "game_id": game_key(date_id, team_id, opponent_id, home_away), "event_id": int(rec["game_event_id"]),
                "season": raw.season, "season_type": season_type, "date_id": date_id, "player_id": player_id,
                "team_id": team_id, "opponent_team_id": opponent_id, "period": _int(rec.get("period")),
                "period_seconds_left": 60 * (_int(rec.get("minutes_remaining")) or 0)
                                       + (_int(rec.get("seconds_remaining")) or 0),
                "action_type": rec.get("action_type"),
                "shot_type": "3PT" if str(rec.get("shot_type", "")).startswith("3") else "2PT",
                "zone_basic": rec.get("shot_zone_basic"), "zone_area": rec.get("shot_zone_area"),
                "zone_range": rec.get("shot_zone_range"), "distance_ft": to_float(rec.get("shot_distance")),
                "loc_x": to_float(rec.get("loc_x")), "loc_y": to_float(rec.get("loc_y")),
                "made": _int(rec.get("shot_made_flag")),
            })

    def _on_off(self, raw, season_type, payload, resolver, result) -> None:
        sets = result_sets(payload)
        for court in ("on", "off"):
            columns, rows = sets.get(f"Players{court.title()}CourtTeamPlayerOnOffDetails", ([], []))
            result.raw_row_count += len(rows)
            for index, row in enumerate(rows):
                rec = dict(zip(columns, row))
                team_id = resolver.team(self.source_name, rec.get("team_abbreviation"), {"file": raw.path.name})
                if team_id is None or not rec.get("vs_player_id"):
                    result.skip(index, "unknown team or player")
                    continue
                person_id = str(int(rec["vs_player_id"]))
                player_id = resolver.known_player(self.source_name, person_id) or resolver.player(
                    self.source_name, person_id, _first_last(rec.get("vs_player_name")), team_id, raw.season,
                    fallback_id=f"nba_{person_id}")
                for stat_name, value in numeric_stats(rec, "on_off").items():
                    result.add("fact_player_season_stat", {
                        "season": raw.season, "season_type": season_type, "player_id": player_id, "split": team_id,
                        "stat_table": "on_off", "stat_name": f"{court}_{stat_name}", "value": value,
                        "team_id": team_id,
                    })

    def _player(self, raw: RawFile, rec: dict, team_id: str | None, resolver: IdResolver, season: int) -> str:
        person_id = int(rec.get("player_id") or rec["close_def_person_id"])
        return resolver.player(self.source_name, str(person_id), rec["player_name"], team_id, season,
                               fallback_id=f"nba_{person_id}")

    def _team(self, raw: RawFile, rec: dict, resolver: IdResolver) -> str | None:
        code = rec.get("team_abbreviation") or rec.get("player_last_team_abbreviation")
        return resolver.team(self.source_name, code, {"file": raw.path.name})

    def _player_bio(self, raw, season_type, records, resolver, result) -> None:
        for index, rec in enumerate(records):
            if season_type != "regular":
                result.skip(index, "bio is taken from the regular season file")
                continue
            player_id = self._player(raw, rec, self._team(raw, rec, resolver), resolver, raw.season)
            result.add("dim_player", {
                "player_id": player_id, "player_name": rec["player_name"], "nba_person_id": int(rec["player_id"]),
                "height": to_float(rec.get("player_height_inches")), "weight": to_float(rec.get("player_weight")),
                "draft_year": _int(rec.get("draft_year")), "draft_round": _int(rec.get("draft_round")),
                "draft_number": _int(rec.get("draft_number")), "college": _text(rec.get("college")),
                "country": _text(rec.get("country")),
            })

    def _player_season(self, raw, base, season_type, records, resolver, result) -> None:
        stat_table, prefix = stat_table_for(base)
        stints: dict[str, list[tuple[str | None, dict[str, float]]]] = {}
        for rec in records:
            team_id = self._team(raw, rec, resolver)
            player_id = self._player(raw, rec, team_id, resolver, raw.season)
            dim = {"player_id": player_id, "player_name": rec["player_name"],
                   "nba_person_id": int(rec.get("player_id") or rec["close_def_person_id"])}
            if season_type == "regular" and stat_table == "totals":
                dim["team_id_current"] = team_id
            result.add("dim_player", dim)

            stints.setdefault(player_id, []).append((team_id, numeric_stats(rec, stat_table)))

        for player_id, player_stints in stints.items():
            rows = [(FULL_SEASON_SPLIT, team_id, stats) for team_id, stats in player_stints]
            if len(player_stints) > 1:
                rows = self._combine_stints(stat_table, player_id, player_stints, result)
            for split, team_id, stats in rows:
                for stat_name, value in stats.items():
                    result.add("fact_player_season_stat", {
                        "season": raw.season, "season_type": season_type, "player_id": player_id,
                        "split": split, "stat_table": stat_table, "stat_name": f"{prefix}{stat_name}",
                        "value": value, "team_id": team_id,
                    })
            self._compact_season(raw, season_type, stat_table, player_id, rows, result)

    @staticmethod
    def _combine_stints(stat_table, player_id, player_stints, result) -> list[tuple]:
        """Several rows for one player in one table: rebuild the full-season line."""
        stats_only = [stats for _, stats in player_stints]
        if stat_table.startswith("play_type_"):  # one row per team: keep them as splits too
            rows = [(team_id or "UNK", team_id, stats) for team_id, stats in player_stints]
            return rows + [(FULL_SEASON_SPLIT, None, combine_play_type_stints(stats_only))]
        last_team = player_stints[-1][0]
        if stat_table in DEFENSE_SHOTS:
            return [(FULL_SEASON_SPLIT, last_team, combine_defense_stints(stat_table, stats_only))]
        team_id, stats = max(player_stints, key=lambda stint: stint[1].get("gp") or 0)
        result.skip(-1, f"{player_id}: {len(player_stints)} rows in {stat_table}; kept the one with most games")
        return [(FULL_SEASON_SPLIT, team_id, stats)]

    def _compact_season(self, raw, season_type, stat_table, player_id, rows, result) -> None:
        if stat_table != "totals" or season_type != "regular":
            return
        for split, team_id, stats in rows:
            if split != FULL_SEASON_SPLIT:
                continue
            games, points = stats.get("gp"), stats.get("pts")
            result.add("fact_player_season", {
                "player_season_id": f"{raw.season}_{player_id}_{FULL_SEASON_SPLIT}", "player_id": player_id,
                "season": raw.season, "team_id": FULL_SEASON_SPLIT, "games": games, "minutes": stats.get("min"),
                "points": points, "rebounds": stats.get("reb"), "assists": stats.get("ast"),
                "ppg": per_game(points, games), "rpg": per_game(stats.get("reb"), games),
                "apg": per_game(stats.get("ast"), games), "plus_minus": stats.get("plus_minus"),
                "efficiency_rating": true_shooting(points, stats.get("fga"), stats.get("fta")),
            })

    def _team_stats(self, raw, base, season_type, records, resolver, result) -> None:
        """Every team table (including base/advanced) into fact_team_season_stat."""
        stat_table, prefix = stat_table_for(base)
        for index, rec in enumerate(records):
            team_id = resolver.team(self.source_name, rec.get("team_abbreviation") or rec.get("team_name"),
                                    {"file": raw.path.name})
            if team_id is None:
                result.skip(index, "unknown team")
                continue
            for stat_name, value in numeric_stats(rec, stat_table).items():
                result.add("fact_team_season_stat", {
                    "season": raw.season, "season_type": season_type, "team_id": team_id,
                    "stat_table": stat_table, "stat_name": f"{prefix}{stat_name}", "value": value,
                })

    def _lineups(self, raw, base, season_type, records, resolver, result) -> None:
        """Lineups identify members by NBA person id; ids are mapped through the player crosswalk."""
        stat_table = base.removeprefix("lineups_")
        for index, rec in enumerate(records):
            team_id = self._team(raw, rec, resolver)
            person_ids = [pid for pid in str(rec.get("group_id") or "").strip("-").split("-") if pid]
            if team_id is None or not person_ids:
                result.skip(index, "unknown team or empty lineup")
                continue
            names = [name.strip() for name in str(rec.get("group_name") or "").split(" - ")]
            if len(names) != len(person_ids):
                names = [""] * len(person_ids)
            members = sorted(
                resolver.known_player(self.source_name, pid)
                or resolver.player(self.source_name, pid, name, team_id, raw.season, fallback_id=f"nba_{pid}")
                for pid, name in zip(person_ids, names)
            )
            lineup_id = f"{team_id}:{'|'.join(members)}"
            result.add("dim_lineup", {"lineup_id": lineup_id, "team_id": team_id, "group_size": len(members),
                                      "player_ids": "|".join(members), "lineup_name": rec.get("group_name")})
            for player_id in members:
                result.add("bridge_lineup_player", {"lineup_id": lineup_id, "player_id": player_id})
            for stat_name, value in numeric_stats(rec, stat_table).items():
                result.add("fact_lineup_season_stat", {
                    "season": raw.season, "season_type": season_type, "lineup_id": lineup_id, "team_id": team_id,
                    "stat_table": stat_table, "stat_name": stat_name, "value": value,
                })

    def _team_season(self, raw, season_type, records, resolver, result) -> None:
        for index, rec in enumerate(records):
            if season_type != "regular":
                result.skip(index, "playoff team season stats are not modeled")
                continue
            team_id = resolver.team(self.source_name, rec.get("team_name"), {"file": raw.path.name})
            if team_id is None:
                result.skip(index, "unknown team")
                continue
            row = {"team_season_id": f"{raw.season}_{team_id}", "team_id": team_id, "season": raw.season}
            if "w" in rec:
                row.update(wins=to_float(rec.get("w")), losses=to_float(rec.get("l")))
            if "off_rating" in rec:
                row.update(off_rtg=to_float(rec.get("off_rating")), def_rtg=to_float(rec.get("def_rating")),
                           net_rtg=to_float(rec.get("net_rating")), pace=to_float(rec.get("pace")))
            result.add("fact_team_season", row)

    def _game_context(self, raw, index, rec, resolver, result):
        match = MATCHUP.match(rec.get("matchup") or "")
        date_id = to_date_id(rec.get("game_date"))
        if not match or date_id is None:
            result.skip(index, f"unparseable matchup/date {rec.get('matchup')!r}")
            return None
        team_id = resolver.team(self.source_name, match[1], {"file": raw.path.name})
        opponent_id = resolver.team(self.source_name, match[3], {"file": raw.path.name})
        if team_id is None or opponent_id is None:
            result.skip(index, "unknown team")
            return None
        home_away = "H" if match[2] == "vs." else "A"
        return date_id, team_id, opponent_id, home_away, game_key(date_id, team_id, opponent_id, home_away)

    def _playoff_date(self, date_id: str, season: int, season_type: str, result: AdapterResult) -> None:
        if season_type == "playoffs":
            result.add("dim_date", {"date_id": date_id, "calendar_date": date_id, "season": season,
                                    "month": int(date_id[5:7]), "year": int(date_id[:4]), "is_playoff": 1})

    def _player_games(self, raw, season_type, records, resolver, result) -> None:
        for index, rec in enumerate(records):
            context = self._game_context(raw, index, rec, resolver, result)
            if context is None:
                continue
            date_id, team_id, opponent_id, home_away, gid = context
            player_id = self._player(raw, rec, team_id, resolver, raw.season)
            result.add("dim_player", {"player_id": player_id, "player_name": rec["player_name"],
                                      "nba_person_id": int(rec["player_id"])})
            self._playoff_date(date_id, raw.season, season_type, result)
            f = {k: to_float(rec.get(k)) for k in ("min", "pts", "reb", "ast", "stl", "blk", "fgm", "fga", "fg3m",
                                                   "fg3a", "ftm", "fta", "oreb", "dreb", "tov", "pf", "plus_minus")}
            result.add("fact_player_game", {
                "player_game_id": f"{date_id}_{player_id}", "player_id": player_id, "team_id": team_id,
                "date_id": date_id, "season": raw.season, "opponent_team_id": opponent_id,
                "game_id": gid, "home_away": home_away, "minutes": f["min"], "points": f["pts"],
                "rebounds": f["reb"], "assists": f["ast"], "steals": f["stl"], "blocks": f["blk"],
                "fgm": f["fgm"], "fga": f["fga"], "fg3m": f["fg3m"], "fg3a": f["fg3a"], "ftm": f["ftm"],
                "fta": f["fta"], "oreb": f["oreb"], "dreb": f["dreb"], "tov": f["tov"], "pf": f["pf"],
                "plus_minus": f["plus_minus"],
            })

    def _team_games(self, raw, season_type, records, resolver, result) -> None:
        for index, rec in enumerate(records):
            context = self._game_context(raw, index, rec, resolver, result)
            if context is None:
                continue
            date_id, team_id, opponent_id, home_away, gid = context
            self._playoff_date(date_id, raw.season, season_type, result)
            f = {k: to_float(rec.get(k)) or 0.0 for k in ("pts", "plus_minus", "fga", "fta", "oreb", "tov", "min")}
            points_against = f["pts"] - f["plus_minus"]
            possessions = team_possessions(f["fga"], f["fta"], f["oreb"], f["tov"])
            row = {
                "team_game_id": f"{date_id}_{team_id}", "team_id": team_id, "opponent_team_id": opponent_id,
                "date_id": date_id, "season": raw.season, "game_id": gid, "home_away": home_away,
                "points_for": f["pts"], "points_against": points_against,
            }
            # Possession-based ratings from the team's own box score (opponent possessions assumed equal).
            if possessions > 0:
                off_rtg = round(100 * f["pts"] / possessions, 1)
                def_rtg = round(100 * points_against / possessions, 1)
                row.update(off_rtg=off_rtg, def_rtg=def_rtg, net_rtg=round(off_rtg - def_rtg, 1),
                           pace=round(possessions * 240 / f["min"], 1) if f["min"] else None)
            result.add("fact_team_game", row)
