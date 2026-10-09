"""Everything you might want to change about the data pipeline, in one place.

Edit a value, save, and the next pull/ingest/export uses it. A command-line option
(python -m pipeline.etl.orchestrator ... --season 2020) or a menu answer
(python -m pipeline) overrides the value here for that one run.

Bad values are caught when the pipeline starts: the error names the setting and
says what is allowed.

Model settings (the residual model) live in pipeline/model/config.py, not here.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Seasons
# ---------------------------------------------------------------------------

# The season "Update current season" pulls. Seasons are labelled by END year:
# 2026 = the 2025-26 season.
# None = work it out from today's date, switching to the next season on Nov 1
# (after every normal opening night). Set a year to pin it, e.g. CURRENT_SEASON = 2026.
CURRENT_SEASON: int | None = None

# Default seasons for "Backfill seasons" (end years; the last year is excluded,
# so range(2017, 2027) = 2016-17 through 2025-26).
# stats.nba.com player tables start in 1996-97 (1997); Basketball-Reference goes back further.
# Cost: about 6 minutes of stats.nba.com requests per season per season type.
SEASONS = range(2017, 2027)

# "regular", "playoffs" or "both".
# "both" doubles stats.nba.com requests (about 6 -> 12 minutes per season).
SEASON_TYPE = "both"

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

# Sources pulled by default, in this order. Allowed: "nba_stats", "bbref", "bbref_team", "darko".
# Keep it a tuple: a single source needs a trailing comma, e.g. ("nba_stats",).
# "darko" must come after "nba_stats": DARKO snapshot dates come from the nba_stats game logs.
# DARKO data: fine to use locally (warehouse, modeling, Tableau Desktop); don't publish it
# (Tableau Public, GitHub, shared files). Commercial use needs DARKO's permission.
DEFAULT_SOURCES = ("nba_stats", "bbref", "bbref_team", "darko")

# Basketball-Reference: also pull season totals, schedule and standings through
# basketball_reference_web_scraper (a few extra requests per season).
BBREF_WITH_WEB_SCRAPER = False

# DARKO: days between rating snapshots within a season. 7 = about 30 requests per season;
# 1 = every game day, about 190 requests per season.
DARKO_EVERY_DAYS = 7

# stats.nba.com: only pull these tables. Empty () = every table.
# Table names are the keys of ALL_TABLES / TEAM_REQUEST_TABLES in
# pipeline/etl/sources/nba_stats/extract.py, e.g. ("player_season_totals", "player_game_log").
NBA_STATS_TABLES: tuple[str, ...] = ()

# ---------------------------------------------------------------------------
# Request pacing (seconds between requests to the same site)
# ---------------------------------------------------------------------------

# stats.nba.com. Lower is faster but risks timeouts and temporary blocks.
NBA_STATS_DELAY_SECONDS = 1.5

# Basketball-Reference. Must be at least 3: faster than about 20 requests a minute gets
# you blocked for about an hour (HTTP 429), which stops the pull.
BBREF_DELAY_SECONDS = 4

# DARKO (www.darko.app). Don't go lower: their terms ask clients not to work around rate limits.
DARKO_DELAY_SECONDS = 3

# ---------------------------------------------------------------------------
# Team tables (pull --source bbref_team)
# ---------------------------------------------------------------------------

# Also write a Tableau-ready Excel workbook per season to data/tableau/team_stats_<season>.xlsx.
TEAM_STATS_EXCEL = True

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

# Write the CSVs in data/clean/ after every "run". False = only when you ask
# (run --export, the menu's "Export CSVs" questions, or the export command).
EXPORT_AFTER_RUN = False

# Minutes a player needs in a season to count in the league percentiles
# (data/clean/analysis/player_season_percentiles.csv).
QUALIFY_MINUTES = {"regular": 500, "playoffs": 100}

# ---------------------------------------------------------------------------
# Folders (relative to the project root). Change only if you move the data.
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
TABLEAU_DIR = DATA_DIR / "tableau"
WAREHOUSE_PATH = DATA_DIR / "warehouse" / "nba_analytics.db"

# ---------------------------------------------------------------------------
# Not settings: allowed values and checks used by the pipeline.
# ---------------------------------------------------------------------------

SOURCE_CHOICES = ("nba_stats", "bbref", "bbref_team", "darko")
SEASON_TYPES = ("regular", "playoffs", "both")
FIRST_NBA_STATS_SEASON = 1997
MIN_BBREF_DELAY_SECONDS = 3


class SettingsError(ValueError):
    """A value in pipeline/settings.py is not allowed. The message starts with the setting name."""


def current_season(today: date | None = None) -> int:
    """CURRENT_SEASON if set; otherwise the season containing today, switching over on Nov 1."""
    if CURRENT_SEASON is not None:
        return CURRENT_SEASON
    today = today or date.today()
    return today.year + 1 if (today.month, today.day) >= (11, 1) else today.year


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate() -> None:
    """Raise SettingsError for the first setting with a value the pipeline can't use."""
    from pipeline.etl.sources.nba_stats.extract import ALL_TABLES, TEAM_REQUEST_TABLES

    if isinstance(DEFAULT_SOURCES, str) or not isinstance(DEFAULT_SOURCES, (tuple, list)):
        raise SettingsError(f'DEFAULT_SOURCES must be a tuple like ("nba_stats",) - note the trailing comma '
                            f"for a single source; got {DEFAULT_SOURCES!r}")
    unknown = [s for s in DEFAULT_SOURCES if s not in SOURCE_CHOICES]
    if unknown or not DEFAULT_SOURCES:
        raise SettingsError(f"DEFAULT_SOURCES: unknown or empty {unknown or DEFAULT_SOURCES!r}; "
                            f"allowed: {', '.join(SOURCE_CHOICES)}")
    if "darko" in DEFAULT_SOURCES and "nba_stats" in DEFAULT_SOURCES and \
            list(DEFAULT_SOURCES).index("darko") < list(DEFAULT_SOURCES).index("nba_stats"):
        raise SettingsError("DEFAULT_SOURCES: put darko after nba_stats (its snapshot dates come from the "
                            "nba_stats game logs)")

    if CURRENT_SEASON is not None and not _is_int(CURRENT_SEASON):
        raise SettingsError(f"CURRENT_SEASON must be None or an end year like 2026; got {CURRENT_SEASON!r}")
    seasons = list(SEASONS)
    if not seasons or not all(_is_int(s) for s in seasons):
        raise SettingsError(f"SEASONS must be end years, e.g. range(2017, 2027); got {SEASONS!r}")
    if "nba_stats" in DEFAULT_SOURCES:
        low = min(seasons + ([CURRENT_SEASON] if CURRENT_SEASON else []))
        if low < FIRST_NBA_STATS_SEASON:
            raise SettingsError(f"SEASONS/CURRENT_SEASON: stats.nba.com starts in {FIRST_NBA_STATS_SEASON} "
                                f"(1996-97); got {low}")

    if SEASON_TYPE not in SEASON_TYPES:
        raise SettingsError(f"SEASON_TYPE must be one of {', '.join(SEASON_TYPES)} (lowercase); got {SEASON_TYPE!r}")
    if not _is_int(DARKO_EVERY_DAYS) or DARKO_EVERY_DAYS < 1:
        raise SettingsError(f"DARKO_EVERY_DAYS must be a whole number of days, 1 or more; got {DARKO_EVERY_DAYS!r}")
    bad_tables = [t for t in NBA_STATS_TABLES if t not in ALL_TABLES and t not in TEAM_REQUEST_TABLES]
    if isinstance(NBA_STATS_TABLES, str) or bad_tables:
        raise SettingsError(f"NBA_STATS_TABLES: unknown table(s) {bad_tables or NBA_STATS_TABLES!r}; see ALL_TABLES "
                            f"in pipeline/etl/sources/nba_stats/extract.py")

    for name, value in (("NBA_STATS_DELAY_SECONDS", NBA_STATS_DELAY_SECONDS),
                        ("DARKO_DELAY_SECONDS", DARKO_DELAY_SECONDS)):
        if not isinstance(value, (int, float)) or value < 0:
            raise SettingsError(f"{name} must be a number of seconds, 0 or more; got {value!r}")
    if not isinstance(BBREF_DELAY_SECONDS, (int, float)) or BBREF_DELAY_SECONDS < MIN_BBREF_DELAY_SECONDS:
        raise SettingsError(f"BBREF_DELAY_SECONDS must be at least {MIN_BBREF_DELAY_SECONDS}: faster gets you "
                            f"blocked by Basketball-Reference for about an hour; got {BBREF_DELAY_SECONDS!r}")

    if not isinstance(QUALIFY_MINUTES, dict) or set(QUALIFY_MINUTES) != {"regular", "playoffs"} or \
            not all(_is_int(v) and v > 0 for v in QUALIFY_MINUTES.values()):
        raise SettingsError(f'QUALIFY_MINUTES must be {{"regular": <minutes>, "playoffs": <minutes>}} with whole '
                            f"numbers above 0; got {QUALIFY_MINUTES!r}")

    for name, value in (("BBREF_WITH_WEB_SCRAPER", BBREF_WITH_WEB_SCRAPER), ("TEAM_STATS_EXCEL", TEAM_STATS_EXCEL),
                        ("EXPORT_AFTER_RUN", EXPORT_AFTER_RUN)):
        if not isinstance(value, bool):
            raise SettingsError(f"{name} must be True or False; got {value!r}")
