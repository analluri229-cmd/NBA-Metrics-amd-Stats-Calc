"""Fetch raw stats.nba.com tables through nba_api. Network only; parsing lives in ``adapter.py``.

Most tables are one request covering every player (or team) in the league. Responses are
saved unmodified (``endpoint.get_dict()``) as data/raw/nba_stats/<season>/<data_type>[_playoffs].json.

Per-team tables (``TEAM_REQUEST_TABLES``) take one request per team, because the endpoint
works per team (on/off) or caps league-wide results (the shot chart stops at 102,400 shots,
about half a season). They are saved as data/raw/nba_stats/<season>/<table>/<TEAM>[_playoffs].json.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ...canonical.dates import season_label
from ...paths import RAW_DIR
from ..pulling import PullReport, with_retries

OUT_ROOT = RAW_DIR / "nba_stats"
REQUEST_DELAY_SECONDS = 1.5
SEASON_TYPES = {"regular": "Regular Season", "playoffs": "Playoffs"}

_PLAYER_DASH = "leaguedashplayerstats.LeagueDashPlayerStats"
_TEAM_DASH = "leaguedashteamstats.LeagueDashTeamStats"
_SHOTS = "leaguedashplayershotlocations.LeagueDashPlayerShotLocations"
_GAME_LOG = "leaguegamelog.LeagueGameLog"
_BIO = "leaguedashplayerbiostats.LeagueDashPlayerBioStats"
_HUSTLE = "leaguehustlestatsplayer.LeagueHustleStatsPlayer"
_CLUTCH = "leaguedashplayerclutch.LeagueDashPlayerClutch"
_TRACKING = "leaguedashptstats.LeagueDashPtStats"
_DEFEND = "leaguedashptdefend.LeagueDashPtDefend"
_SYNERGY = "synergyplaytypes.SynergyPlayTypes"
_TEAM_HUSTLE = "leaguehustlestatsteam.LeagueHustleStatsTeam"
_TEAM_CLUTCH = "leaguedashteamclutch.LeagueDashTeamClutch"
_TEAM_DEFEND = "leaguedashptteamdefend.LeagueDashPtTeamDefend"
_LINEUPS = "leaguedashlineups.LeagueDashLineups"
_PT_SHOT = "leaguedashplayerptshot.LeagueDashPlayerPtShot"
_SHOT_CHART = "shotchartdetail.ShotChartDetail"
_ON_OFF = "teamplayeronoffdetails.TeamPlayerOnOffDetails"

OFFENSIVE_PLAY_TYPES = ("Isolation", "Transition", "PRBallHandler", "PRRollman", "Postup", "Spotup", "Handoff",
                        "Cut", "OffScreen", "OffRebound", "Misc")
DEFENSIVE_PLAY_TYPES = ("Isolation", "PRBallHandler", "PRRollman", "Postup", "Spotup", "Handoff", "OffScreen")


TRACKING_MEASURES = ("SpeedDistance", "Possessions", "Drives", "Passing", "CatchShoot", "PullUpShot", "Rebounding",
                     "PostTouch", "ElbowTouch", "PaintTouch", "Efficiency", "Defense")
DEFENSE_CATEGORIES = (("overall", "Overall"), ("3pt", "3 Pointers"), ("rim", "Less Than 6Ft"))
# Shooter-side tracking splits: distance of the closest defender x time left on the shot clock.
# Each pair is one request; the seven shot clock ranges cover every shot, so summing over them
# gives the defender-distance total.
CLOSEST_DEFENDER_RANGES = {"very_tight": "0-2 Feet - Very Tight", "tight": "2-4 Feet - Tight",
                           "open": "4-6 Feet - Open", "wide_open": "6+ Feet - Wide Open"}
SHOT_CLOCK_RANGES = {"clock_24_22": "24-22", "clock_22_18": "22-18 Very Early", "clock_18_15": "18-15 Early",
                     "clock_15_7": "15-7 Average", "clock_7_4": "7-4 Late", "clock_4_0": "4-0 Very Late",
                     "clock_off": "ShotClock Off"}


def _snake(name: str) -> str:
    """'SpeedDistance' -> 'speed_distance', 'PRBallHandler' -> 'pr_ball_handler'."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def _shared_tables(prefix: str, entity: str) -> dict[str, tuple[str, dict]]:
    """Hustle, clutch, tracking, closest-defender and play type tables for players or teams."""
    player = entity == "player"
    return {
        # Hustle and clutch (NBA's standard clutch: last 5 minutes, score within 5).
        f"{prefix}_hustle": (_HUSTLE if player else _TEAM_HUSTLE, {}),
        f"{prefix}_clutch": (_CLUTCH if player else _TEAM_CLUTCH,
                             {"measure_type_detailed_defense": "Base", "per_mode_detailed": "Totals"}),
        f"{prefix}_clutch_advanced": (_CLUTCH if player else _TEAM_CLUTCH,
                                      {"measure_type_detailed_defense": "Advanced", "per_mode_detailed": "Totals"}),
        # Tracking (Second Spectrum), one table per measure.
        **{
            f"{prefix}_tracking_{_snake(measure)}": (
                _TRACKING, {"pt_measure_type": measure, "player_or_team": entity.title(), "per_mode_simple": "Totals"})
            for measure in TRACKING_MEASURES
        },
        # Opponent shooting against the player (as closest defender) or the team.
        **{
            f"{prefix}_defense_{name}": (_DEFEND if player else _TEAM_DEFEND,
                                         {"defense_category": category, "per_mode_simple": "Totals"})
            for name, category in DEFENSE_CATEGORIES
        },
        # Synergy play types; NBA only tracks the defensive side for seven of them.
        **{
            f"{prefix}_play_type_{_snake(play_type)}_{side}": (
                _SYNERGY, {"play_type_nullable": play_type, "type_grouping_nullable": grouping,
                           "player_or_team_abbreviation": "P" if player else "T", "per_mode_simple": "Totals"})
            for side, grouping, play_types in (
                ("offense", "offensive", OFFENSIVE_PLAY_TYPES), ("defense", "defensive", DEFENSIVE_PLAY_TYPES))
            for play_type in play_types
        },
    }


# data_type -> (nba_api endpoint, parameters)
PLAYER_SEASON_TABLES = {
    "player_season_totals": (_PLAYER_DASH, {"measure_type_detailed_defense": "Base", "per_mode_detailed": "Totals"}),
    "player_season_per_game": (_PLAYER_DASH, {"measure_type_detailed_defense": "Base", "per_mode_detailed": "PerGame"}),
    "player_season_per_36": (_PLAYER_DASH, {"measure_type_detailed_defense": "Base", "per_mode_detailed": "Per36"}),
    "player_season_per_100": (_PLAYER_DASH, {"measure_type_detailed_defense": "Base",
                                             "per_mode_detailed": "Per100Possessions"}),
    "player_season_advanced": (_PLAYER_DASH, {"measure_type_detailed_defense": "Advanced", "per_mode_detailed": "Totals"}),
    "player_season_scoring": (_PLAYER_DASH, {"measure_type_detailed_defense": "Scoring", "per_mode_detailed": "Totals"}),
    "player_season_misc": (_PLAYER_DASH, {"measure_type_detailed_defense": "Misc", "per_mode_detailed": "Totals"}),
    "player_season_usage": (_PLAYER_DASH, {"measure_type_detailed_defense": "Usage", "per_mode_detailed": "Totals"}),
    "player_season_shot_zones": (_SHOTS, {"distance_range": "By Zone", "per_mode_detailed": "Totals"}),
    "player_season_shot_distance": (_SHOTS, {"distance_range": "5ft Range", "per_mode_detailed": "Totals"}),
    **_shared_tables("player_season", "player"),
    **{
        f"player_season_shot_context_{defender}_{clock}": (
            _PT_SHOT, {"close_def_dist_range_nullable": defender_range, "shot_clock_range_nullable": clock_range,
                       "per_mode_simple": "Totals"})
        for defender, defender_range in CLOSEST_DEFENDER_RANGES.items()
        for clock, clock_range in SHOT_CLOCK_RANGES.items()
    },
}
# Season bio (height, weight, draft, college, country) -> dim_player.
PLAYER_BIO = {"player_bio": (_BIO, {"per_mode_simple": "Totals"})}
TEAM_TABLES = {
    "team_season_stats": (_TEAM_DASH, {"measure_type_detailed_defense": "Base", "per_mode_detailed": "Totals"}),
    "team_season_advanced": (_TEAM_DASH, {"measure_type_detailed_defense": "Advanced", "per_mode_detailed": "Totals"}),
}
# Team season tables beyond the base/advanced pair above, stored in fact_team_season_stat.
TEAM_SEASON_TABLES = {
    "team_season_four_factors": (_TEAM_DASH, {"measure_type_detailed_defense": "Four Factors",
                                              "per_mode_detailed": "Totals"}),
    "team_season_opponent": (_TEAM_DASH, {"measure_type_detailed_defense": "Opponent", "per_mode_detailed": "Totals"}),
    **_shared_tables("team_season", "team"),
}
GAME_LOGS = {
    "team_game_log": (_GAME_LOG, {"player_or_team_abbreviation": "T"}),
    "player_game_log": (_GAME_LOG, {"player_or_team_abbreviation": "P"}),
}
# Lineup stats; loaded after the player tables so every lineup member already has a canonical id.
LINEUP_TABLES = {
    "lineups_5man": (_LINEUPS, {"group_quantity": 5, "measure_type_detailed_defense": "Base",
                                "per_mode_detailed": "Totals"}),
    "lineups_5man_advanced": (_LINEUPS, {"group_quantity": 5, "measure_type_detailed_defense": "Advanced",
                                         "per_mode_detailed": "Totals"}),
    "lineups_2man_advanced": (_LINEUPS, {"group_quantity": 2, "measure_type_detailed_defense": "Advanced",
                                         "per_mode_detailed": "Totals"}),
}
ALL_TABLES = {**TEAM_TABLES, **TEAM_SEASON_TABLES, **PLAYER_BIO, **PLAYER_SEASON_TABLES, **GAME_LOGS, **LINEUP_TABLES}


def _shot_chart_params(team_id: int, season: int, season_type: str) -> dict:
    return {"team_id": team_id, "player_id": 0, "season_nullable": season_label(season),
            "season_type_all_star": SEASON_TYPES[season_type], "context_measure_simple": "FGA"}


def _on_off_params(team_id: int, season: int, season_type: str) -> dict:
    return {"team_id": team_id, "season": season_label(season), "season_type_all_star": SEASON_TYPES[season_type],
            "measure_type_detailed_defense": "Base", "per_mode_detailed": "Totals"}


# table -> (nba_api endpoint, parameters for one team). Loaded after the player tables.
TEAM_REQUEST_TABLES = {
    # Every field goal attempt: location, zone, distance, action type, made or missed.
    "shot_chart": (_SHOT_CHART, _shot_chart_params),
    # Team box score with each player on and off the court.
    "on_off": (_ON_OFF, _on_off_params),
}


def nba_teams() -> list[tuple[int, str]]:
    """(stats.nba.com team id, abbreviation) for the 30 franchises; ids are stable across relocations."""
    from nba_api.stats.static import teams

    return sorted((team["id"], team["abbreviation"]) for team in teams.get_teams())


def _endpoint(path: str):
    import importlib

    module_name, class_name = path.split(".")
    module = importlib.import_module(f"nba_api.stats.endpoints.{module_name}")
    return getattr(module, class_name)


def raw_path(season: int, data_type: str, season_type: str = "regular", out_root: Path = OUT_ROOT) -> Path:
    suffix = "" if season_type == "regular" else f"_{season_type}"
    return out_root / str(season) / f"{data_type}{suffix}.json"


def pull_season(season: int, tables: list[str] | None = None, season_types: list[str] | None = None,
                out_root: Path = OUT_ROOT, delay: float = REQUEST_DELAY_SECONDS, timeout: int = 60,
                skip_existing: bool = False, retries: int = 3) -> PullReport:
    """Download each table; a table that keeps failing is reported and the pull continues."""
    unknown = set(tables or ()) - set(ALL_TABLES) - set(TEAM_REQUEST_TABLES)
    if unknown:
        raise ValueError(f"unknown nba_stats tables: {sorted(unknown)}")
    league_tables = [t for t in tables or ALL_TABLES if t in ALL_TABLES]
    team_tables = [t for t in tables or TEAM_REQUEST_TABLES if t in TEAM_REQUEST_TABLES]
    report = PullReport()
    requested = False
    for season_type in season_types or ["regular"]:
        for data_type in league_tables:
            path = raw_path(season, data_type, season_type, out_root)
            if skip_existing and path.exists():
                report.skipped.append(path)
                continue
            endpoint_path, params = ALL_TABLES[data_type]
            if requested:
                time.sleep(delay)
            requested = True

            def fetch() -> dict:
                return _endpoint(endpoint_path)(
                    season=season_label(season), season_type_all_star=SEASON_TYPES[season_type], timeout=timeout,
                    **params,
                ).get_dict()

            try:
                payload = with_retries(fetch, retries)
            except Exception as exc:  # reported; the rest of the season still downloads
                report.failed.append((f"{season} {data_type} ({season_type})", f"{type(exc).__name__}: {exc}"))
                print(f"  FAILED {data_type} ({season_type}): {type(exc).__name__}: {exc}")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")
            report.written.append(path)
            print(f"  saved {data_type} ({season_type}) -> {path}")
    if team_tables:
        report.merge(pull_team_tables(season, team_tables, season_types, out_root, delay,
                                      skip_existing=skip_existing, retries=retries))
    return report


def team_raw_path(season: int, table: str, team: str, season_type: str = "regular",
                  out_root: Path = OUT_ROOT) -> Path:
    suffix = "" if season_type == "regular" else f"_{season_type}"
    return out_root / str(season) / table / f"{team}{suffix}.json"


def pull_team_tables(season: int, tables: list[str] | None = None, season_types: list[str] | None = None,
                     out_root: Path = OUT_ROOT, delay: float = REQUEST_DELAY_SECONDS, timeout: int = 120,
                     skip_existing: bool = False, retries: int = 3) -> PullReport:
    """One request per team for each table in ``TEAM_REQUEST_TABLES``."""
    report = PullReport()
    requested = False
    for season_type in season_types or ["regular"]:
        for table in tables or list(TEAM_REQUEST_TABLES):
            endpoint_path, params_for = TEAM_REQUEST_TABLES[table]
            saved = 0
            for team_id, team in nba_teams():
                path = team_raw_path(season, table, team, season_type, out_root)
                if skip_existing and path.exists():
                    report.skipped.append(path)
                    continue
                if requested:
                    time.sleep(delay)
                requested = True
                params = params_for(team_id, season, season_type)

                def fetch() -> dict:
                    return _endpoint(endpoint_path)(timeout=timeout, **params).get_dict()

                try:
                    payload = with_retries(fetch, retries)
                except Exception as exc:  # reported; the other teams still download
                    report.failed.append((f"{season} {table} {team} ({season_type})", f"{type(exc).__name__}: {exc}"))
                    print(f"  FAILED {table} {team} ({season_type}): {type(exc).__name__}: {exc}")
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload), encoding="utf-8")
                report.written.append(path)
                saved += 1
            print(f"  saved {table} ({season_type}) for {saved} teams -> {out_root / str(season) / table}")
    return report
