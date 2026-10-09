"""Canonical warehouse tables: the single definition used for DDL, validation and writes.

Merge rules per table:
- Tables with a ``source_system`` column but without it in the primary key use
  source precedence (see ``SOURCE_PRECEDENCE``): a higher-priority source wins
  each column, a lower-priority source only fills gaps.
- ``fill_only`` columns never overwrite an existing value.
- All other columns take the incoming value unless it is NULL.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Higher wins when two sources supply the same canonical row.
SOURCE_PRECEDENCE = {"nba_stats": 3, "basketball_reference": 2, "legacy_sample": 1}

# split value for a player's full-season line (all teams combined).
FULL_SEASON_SPLIT = "TOT"


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[tuple[str, str], ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[str, ...] = ()
    fill_only: frozenset[str] = field(default_factory=frozenset)

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.columns)

    @property
    def uses_precedence(self) -> bool:
        return "source_system" in self.column_names and "source_system" not in self.primary_key

    def ddl(self) -> str:
        parts = [f"    {name} {sql_type}" for name, sql_type in self.columns]
        parts.append(f"    PRIMARY KEY ({', '.join(self.primary_key)})")
        parts.extend(f"    FOREIGN KEY{fk}" for fk in self.foreign_keys)
        return f"CREATE TABLE IF NOT EXISTS {self.name} (\n" + ",\n".join(parts) + "\n);"


def _real(*names: str) -> tuple[tuple[str, str], ...]:
    return tuple((name, "REAL") for name in names)


BOX_COLUMNS = _real("fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "tov", "pf", "plus_minus")
TRACE_COLUMNS = (("source_system", "TEXT"), ("run_id", "TEXT"))

TABLES: dict[str, Table] = {
    t.name: t
    for t in (
        Table(
            "dim_date",
            (("date_id", "TEXT NOT NULL"), ("calendar_date", "TEXT NOT NULL"), ("season", "INTEGER"),
             ("month", "INTEGER"), ("year", "INTEGER"), ("is_playoff", "INTEGER DEFAULT 0")),
            ("date_id",),
        ),
        Table(
            "dim_team",
            (("team_id", "TEXT NOT NULL"), ("team_name", "TEXT NOT NULL"), ("abbreviation", "TEXT"),
             ("city", "TEXT"), ("conference", "TEXT"), ("division", "TEXT")),
            ("team_id",),
            fill_only=frozenset({"team_name"}),
        ),
        Table(
            "dim_player",
            (("player_id", "TEXT NOT NULL"), ("player_name", "TEXT NOT NULL"), ("position", "TEXT"),
             ("height", "REAL"), ("weight", "REAL"), ("birth_date", "TEXT"), ("draft_year", "INTEGER"),
             ("team_id_current", "TEXT"), ("nba_person_id", "INTEGER"), ("draft_round", "INTEGER"),
             ("draft_number", "INTEGER"), ("college", "TEXT"), ("country", "TEXT")),
            ("player_id",),
            ("(team_id_current) REFERENCES dim_team(team_id)",),
            fill_only=frozenset({"player_name"}),
        ),
        Table(
            "fact_player_game",
            (("player_game_id", "TEXT NOT NULL"), ("player_id", "TEXT NOT NULL"), ("team_id", "TEXT"),
             ("date_id", "TEXT"), ("season", "INTEGER"), ("opponent_team_id", "TEXT"), ("game_id", "TEXT"),
             ("home_away", "TEXT"), ("minutes", "REAL"), ("points", "REAL"), ("rebounds", "REAL"),
             ("assists", "REAL"), ("steals", "REAL"), ("blocks", "REAL"), *BOX_COLUMNS,
             ("usage_proxy", "REAL"), ("efficiency_proxy", "REAL"), *TRACE_COLUMNS),
            ("player_game_id",),
            ("(player_id) REFERENCES dim_player(player_id)", "(team_id) REFERENCES dim_team(team_id)",
             "(date_id) REFERENCES dim_date(date_id)"),
        ),
        Table(
            "fact_team_game",
            (("team_game_id", "TEXT NOT NULL"), ("team_id", "TEXT NOT NULL"), ("opponent_team_id", "TEXT"),
             ("date_id", "TEXT"), ("season", "INTEGER"), ("game_id", "TEXT"), ("home_away", "TEXT"),
             ("points_for", "REAL"), ("points_against", "REAL"), ("pace", "REAL"), ("off_rtg", "REAL"),
             ("def_rtg", "REAL"), ("net_rtg", "REAL"), *TRACE_COLUMNS),
            ("team_game_id",),
            ("(team_id) REFERENCES dim_team(team_id)", "(date_id) REFERENCES dim_date(date_id)"),
        ),
        Table(
            # Compact regular-season summary. team_id is 'TOT' for a full-season line.
            "fact_player_season",
            (("player_season_id", "TEXT NOT NULL"), ("player_id", "TEXT NOT NULL"), ("season", "INTEGER"),
             ("team_id", "TEXT"), ("games", "REAL"), ("games_started", "REAL"), ("minutes", "REAL"),
             ("points", "REAL"), ("rebounds", "REAL"), ("assists", "REAL"), ("ppg", "REAL"), ("rpg", "REAL"),
             ("apg", "REAL"), ("plus_minus", "REAL"), ("usage_rate", "REAL"), ("efficiency_rating", "REAL"),
             *TRACE_COLUMNS),
            ("player_season_id",),
            ("(player_id) REFERENCES dim_player(player_id)",),
        ),
        Table(
            # Every player season stat table from every source, one row per stat.
            # source_system is part of the key: sources define some stats differently
            # (e.g. usage as 0.25 vs 25.0), so they are kept side by side, never merged.
            "fact_player_season_stat",
            (("season", "INTEGER NOT NULL"), ("season_type", "TEXT NOT NULL"), ("player_id", "TEXT NOT NULL"),
             ("split", "TEXT NOT NULL"), ("source_system", "TEXT NOT NULL"), ("stat_table", "TEXT NOT NULL"),
             ("stat_name", "TEXT NOT NULL"), ("value", "REAL"), ("team_id", "TEXT"), ("run_id", "TEXT")),
            ("season", "season_type", "player_id", "split", "source_system", "stat_table", "stat_name"),
            ("(player_id) REFERENCES dim_player(player_id)",),
        ),
        Table(
            # Every field goal attempt (stats.nba.com shot chart). loc_x/loc_y are in tenths of a foot
            # from the basket (x: sideline to sideline, y: toward half court); period_seconds_left is the
            # game clock, not the shot clock.
            "fact_shot",
            (("game_id", "TEXT NOT NULL"), ("event_id", "INTEGER NOT NULL"), ("season", "INTEGER"),
             ("season_type", "TEXT"), ("date_id", "TEXT"), ("player_id", "TEXT NOT NULL"), ("team_id", "TEXT"),
             ("opponent_team_id", "TEXT"), ("period", "INTEGER"), ("period_seconds_left", "INTEGER"),
             ("action_type", "TEXT"), ("shot_type", "TEXT"), ("zone_basic", "TEXT"), ("zone_area", "TEXT"),
             ("zone_range", "TEXT"), ("distance_ft", "REAL"), ("loc_x", "REAL"), ("loc_y", "REAL"),
             ("made", "INTEGER"), *TRACE_COLUMNS),
            ("game_id", "event_id"),
            ("(player_id) REFERENCES dim_player(player_id)",),
        ),
        Table(
            # Player ratings as published on a date (DARKO DPM). date_id is the last game date the
            # rating includes; to avoid leakage, join a game on date G to the latest date_id < G.
            "fact_player_rating_daily",
            (("date_id", "TEXT NOT NULL"), ("season", "INTEGER NOT NULL"), ("player_id", "TEXT NOT NULL"),
             ("team_id", "TEXT"), ("source_system", "TEXT NOT NULL"), ("stat_table", "TEXT NOT NULL"),
             ("stat_name", "TEXT NOT NULL"), ("value", "REAL"), ("run_id", "TEXT")),
            ("date_id", "player_id", "source_system", "stat_table", "stat_name"),
            ("(player_id) REFERENCES dim_player(player_id)",),
        ),
        Table(
            "fact_team_season",
            (("team_season_id", "TEXT NOT NULL"), ("team_id", "TEXT NOT NULL"), ("season", "INTEGER"),
             ("wins", "REAL"), ("losses", "REAL"), ("off_rtg", "REAL"), ("def_rtg", "REAL"), ("net_rtg", "REAL"),
             ("pace", "REAL"), ("playoff_appearance", "INTEGER"), *TRACE_COLUMNS),
            ("team_season_id",),
            ("(team_id) REFERENCES dim_team(team_id)",),
        ),
        Table(
            # Basketball-Reference team/opponent x totals/per-100 tables (pull --source bbref_team).
            "fact_team_season_box",
            (("team_season_box_id", "TEXT NOT NULL"), ("team_id", "TEXT NOT NULL"), ("season", "INTEGER"),
             ("perspective", "TEXT"), ("stat_basis", "TEXT"),
             *_real("g", "mp", "fg", "fga", "fg_pct", "fg3", "fg3a", "fg3_pct", "fg2", "fg2a", "fg2_pct",
                    "ft", "fta", "ft_pct", "orb", "drb", "trb", "ast", "stl", "blk", "tov", "pf", "pts"),
             *TRACE_COLUMNS),
            ("team_season_box_id",),
            ("(team_id) REFERENCES dim_team(team_id)",),
        ),
        Table(
            # Team season stats from every source, one row per stat (the team counterpart of
            # fact_player_season_stat; stat tables share names with the player versions).
            "fact_team_season_stat",
            (("season", "INTEGER NOT NULL"), ("season_type", "TEXT NOT NULL"), ("team_id", "TEXT NOT NULL"),
             ("source_system", "TEXT NOT NULL"), ("stat_table", "TEXT NOT NULL"), ("stat_name", "TEXT NOT NULL"),
             ("value", "REAL"), ("run_id", "TEXT")),
            ("season", "season_type", "team_id", "source_system", "stat_table", "stat_name"),
            ("(team_id) REFERENCES dim_team(team_id)",),
        ),
        Table(
            # A set of players who shared the floor for one team. lineup_id = <team>:<sorted player ids>.
            "dim_lineup",
            (("lineup_id", "TEXT NOT NULL"), ("team_id", "TEXT"), ("group_size", "INTEGER"),
             ("player_ids", "TEXT"), ("lineup_name", "TEXT")),
            ("lineup_id",),
            ("(team_id) REFERENCES dim_team(team_id)",),
        ),
        Table(
            "bridge_lineup_player",
            (("lineup_id", "TEXT NOT NULL"), ("player_id", "TEXT NOT NULL")),
            ("lineup_id", "player_id"),
            ("(lineup_id) REFERENCES dim_lineup(lineup_id)", "(player_id) REFERENCES dim_player(player_id)"),
        ),
        Table(
            "fact_lineup_season_stat",
            (("season", "INTEGER NOT NULL"), ("season_type", "TEXT NOT NULL"), ("lineup_id", "TEXT NOT NULL"),
             ("team_id", "TEXT"), ("source_system", "TEXT NOT NULL"), ("stat_table", "TEXT NOT NULL"),
             ("stat_name", "TEXT NOT NULL"), ("value", "REAL"), ("run_id", "TEXT")),
            ("season", "season_type", "lineup_id", "source_system", "stat_table", "stat_name"),
            ("(lineup_id) REFERENCES dim_lineup(lineup_id)",),
        ),
        Table(
            # Data dictionary for the *_season_stat tables (rebuilt by stat_catalog.refresh_stat_catalog).
            # entity: player, team or lineup.
            "dim_stat",
            (("entity", "TEXT NOT NULL"), ("source_system", "TEXT NOT NULL"), ("stat_table", "TEXT NOT NULL"),
             ("stat_name", "TEXT NOT NULL"), ("label", "TEXT"), ("category", "TEXT"), ("unit", "TEXT"),
             ("basis", "TEXT"), ("higher_is_better", "INTEGER"), ("definition", "TEXT"), ("documented", "INTEGER")),
            ("entity", "source_system", "stat_table", "stat_name"),
        ),
        Table(
            "xref_team",
            (("source_name", "TEXT NOT NULL"), ("source_key", "TEXT NOT NULL"), ("team_id", "TEXT NOT NULL")),
            ("source_name", "source_key"),
        ),
        Table(
            "xref_player",
            (("source_name", "TEXT NOT NULL"), ("source_key", "TEXT NOT NULL"), ("player_id", "TEXT NOT NULL"),
             ("player_name", "TEXT"), ("match_method", "TEXT")),
            ("source_name", "source_key"),
        ),
        Table(
            # Review queue: names/teams an adapter could not map to a canonical id.
            "unresolved_entity",
            (("entity_type", "TEXT NOT NULL"), ("source_name", "TEXT NOT NULL"), ("source_key", "TEXT NOT NULL"),
             ("raw_value", "TEXT"), ("fallback_id", "TEXT"), ("context", "TEXT"), ("run_id", "TEXT")),
            ("entity_type", "source_name", "source_key"),
        ),
        Table(
            "source_manifest",
            (("source_name", "TEXT NOT NULL"), ("run_id", "TEXT NOT NULL"), ("run_timestamp", "TEXT NOT NULL"),
             ("source_file", "TEXT"), ("rows_inserted", "INTEGER DEFAULT 0"), ("rows_updated", "INTEGER DEFAULT 0"),
             ("rows_skipped", "INTEGER DEFAULT 0"), ("status", "TEXT NOT NULL DEFAULT 'success'"),
             ("source_system", "TEXT"), ("data_type", "TEXT"), ("season", "INTEGER"), ("file_sha256", "TEXT"),
             ("raw_row_count", "INTEGER"), ("rows_unresolved", "INTEGER DEFAULT 0"), ("error", "TEXT")),
            ("source_name", "run_id"),
        ),
    )
}

# Order rows are written in so foreign keys are satisfied.
LOAD_ORDER = (
    "dim_team", "dim_date", "dim_player", "dim_lineup", "bridge_lineup_player",
    "fact_team_season", "fact_team_season_box", "fact_team_season_stat",
    "fact_player_season", "fact_player_season_stat", "fact_player_rating_daily", "fact_lineup_season_stat",
    "fact_team_game", "fact_player_game", "fact_shot",
    "xref_team", "xref_player", "unresolved_entity",
)

# Derived tables rebuilt from the facts on every run; recreated when their definition changes.
DERIVED_TABLES = frozenset({"dim_stat"})

# (fact table, entity, id column) for the long stat tables the data dictionary covers.
STAT_TABLES = (("fact_player_season_stat", "player", "player_id"), ("fact_team_season_stat", "team", "team_id"),
               ("fact_lineup_season_stat", "lineup", "lineup_id"), ("fact_player_rating_daily", "player", "player_id"))

FACT_TABLES = tuple(name for name in LOAD_ORDER if name.startswith("fact_"))

# Loader-owned tables adapters may not write directly.
ADAPTER_WRITABLE = frozenset(LOAD_ORDER) - {"xref_team", "xref_player", "unresolved_entity"}


def schema_sql() -> str:
    return "\n\n".join(table.ddl() for table in TABLES.values())
