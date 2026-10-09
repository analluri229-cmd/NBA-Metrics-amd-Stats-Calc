"""Export canonical warehouse tables and notebook-ready views to CSV.

Scope: by default the latest season, written to data/clean/. ``--season N`` writes
data/clean/season_<N>/ and ``--all-seasons`` writes every season to data/clean/.
Fact and feature tables are filtered to the scope; dimensions, crosswalks, the
stat dictionary and the manifest are always complete. The long
fact_*_season_stat and fact_player_rating_daily tables stay in the warehouse only: the
wide player_season/, team_season/, lineup_season/ and player_rating_daily/ files hold
the same values at a fraction of the size.

Output:
    <table>.csv                      canonical tables, feature table and manifest
    analysis/player_games.csv        player games joined with names, plus per-36 rates
    analysis/team_seasons.csv        team seasons joined with names and conference
    player_season/<source>_<stat_table>.csv
                                     fact_player_season_stat pivoted wide: one row per
                                     (season, season_type, player, split), one column per stat
    team_season/<source>_<stat_table>.csv     one row per (season, season_type, team)
    lineup_season/<source>_<stat_table>.csv   one row per (season, season_type, lineup)
    player_rating_daily/<source>_<stat_table>.csv
                                     dated ratings (DARKO): one row per (rating date, player)
    dim_stat.csv                     data dictionary (entity = player/team/lineup): label,
                                     definition, unit, basis, direction
    analysis/player_season_percentiles.csv
                                     every full-season stat with its league percentile among
                                     qualified players (QUALIFY_MINUTES)
    analysis/team_season_ranks.csv   every team stat ranked 1-30 (1 = best when the stat has a
                                     direction, else 1 = highest)
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from pipeline.etl.canonical.schema import TABLES
from pipeline.etl.paths import CLEAN_DIR, DB_PATH

# Kept in the warehouse only; the *_season/ wide files hold the same values.
WAREHOUSE_ONLY = {"fact_player_season_stat", "fact_team_season_stat", "fact_lineup_season_stat",
                  "fact_player_rating_daily"}
EXPORT_TABLES = [*(t for t in TABLES if t not in WAREHOUSE_ONLY), "feature_player_daily"]
SEASON_SCOPED_PREFIXES = ("fact_", "feature_")

# Percentiles only rank players with enough minutes for the stat to mean something.
QUALIFY_MINUTES = {"regular": 500, "playoffs": 100}
MINUTES_STAT = {"basketball_reference": ("totals", "mp"), "nba_stats": ("totals", "min")}

PLAYER_GAMES_SQL = """
SELECT g.season, g.date_id, g.game_id, g.player_id, p.player_name, g.team_id, t.team_name,
       g.opponent_team_id, o.team_name AS opponent_name, g.home_away, g.minutes, g.points, g.rebounds,
       g.assists, g.steals, g.blocks, g.fgm, g.fga, g.fg3m, g.fg3a, g.ftm, g.fta, g.oreb, g.dreb, g.tov, g.pf,
       g.plus_minus, g.usage_proxy, g.efficiency_proxy,
       CASE WHEN g.minutes > 0 THEN ROUND(g.points * 36.0 / g.minutes, 2) END AS pts_per36,
       CASE WHEN g.minutes > 0 THEN ROUND(g.rebounds * 36.0 / g.minutes, 2) END AS reb_per36,
       CASE WHEN g.minutes > 0 THEN ROUND(g.assists * 36.0 / g.minutes, 2) END AS ast_per36,
       g.source_system, g.run_id
FROM fact_player_game g
LEFT JOIN dim_player p ON p.player_id = g.player_id
LEFT JOIN dim_team t ON t.team_id = g.team_id
LEFT JOIN dim_team o ON o.team_id = g.opponent_team_id
{where}
ORDER BY g.date_id, g.team_id, g.player_id
"""

TEAM_SEASONS_SQL = """
SELECT s.season, s.team_id, t.team_name, t.conference, t.division, s.wins, s.losses, s.off_rtg, s.def_rtg,
       s.net_rtg, s.pace, s.playoff_appearance, s.source_system, s.run_id
FROM fact_team_season s
LEFT JOIN dim_team t ON t.team_id = s.team_id
{where}
ORDER BY s.season, s.team_id
"""


def _read(conn: sqlite3.Connection, sql: str, season: int | None, alias: str = "") -> pd.DataFrame:
    where = f"WHERE {alias}season = ?" if season is not None else ""
    return pd.read_sql_query(sql.format(where=where), conn, params=(season,) if season is not None else ())


WIDE_EXPORTS = {
    # folder: (query, index columns)
    "player_season": ("""
        SELECT s.season, s.season_type, s.player_id, p.player_name, s.split, s.team_id, s.source_system,
               s.stat_table, s.stat_name, s.value
        FROM fact_player_season_stat s LEFT JOIN dim_player p ON p.player_id = s.player_id
        {where} ORDER BY s.rowid""", ["season", "season_type", "player_id", "player_name", "split", "team_id"]),
    "team_season": ("""
        SELECT s.season, s.season_type, s.team_id, t.team_name, s.source_system, s.stat_table, s.stat_name, s.value
        FROM fact_team_season_stat s LEFT JOIN dim_team t ON t.team_id = s.team_id
        {where} ORDER BY s.rowid""", ["season", "season_type", "team_id", "team_name"]),
    "lineup_season": ("""
        SELECT s.season, s.season_type, s.lineup_id, s.team_id, l.group_size, l.lineup_name, s.source_system,
               s.stat_table, s.stat_name, s.value
        FROM fact_lineup_season_stat s LEFT JOIN dim_lineup l ON l.lineup_id = s.lineup_id
        {where} ORDER BY s.rowid""", ["season", "season_type", "lineup_id", "team_id", "group_size", "lineup_name"]),
    "player_rating_daily": ("""
        SELECT s.season, s.date_id, s.player_id, p.player_name, s.team_id, s.source_system, s.stat_table,
               s.stat_name, s.value
        FROM fact_player_rating_daily s LEFT JOIN dim_player p ON p.player_id = s.player_id
        {where} ORDER BY s.rowid""", ["season", "date_id", "player_id", "player_name", "team_id"]),
}


def export_wide(conn: sqlite3.Connection, folder: str, out_dir: Path, season: int | None = None) -> dict[str, str]:
    """Pivot one long stat table to one CSV per (source, stat table): a row per entity, a column per stat."""
    sql, index = WIDE_EXPORTS[folder]
    long = _read(conn, sql, season, "s.")
    exports: dict[str, str] = {}
    if long.empty:
        return exports
    out_dir.mkdir(parents=True, exist_ok=True)
    text_keys = [c for c in index if long[c].dtype == object]
    long[text_keys] = long[text_keys].fillna("")  # keep rows with NULL keys
    for (source, stat_table), group in long.groupby(["source_system", "stat_table"], sort=True):
        stat_order = list(dict.fromkeys(group["stat_name"]))  # keep the source's column order
        wide = group.set_index([*index, "stat_name"])["value"].unstack("stat_name")
        wide = wide.reindex(columns=stat_order).reset_index()
        wide.columns.name = None
        path = out_dir / f"{source}_{stat_table}.csv"
        wide.sort_values(index[:3]).to_csv(path, index=False)
        exports[f"{folder}/{source}_{stat_table}"] = str(path)
    return exports


def export_player_season_wide(conn: sqlite3.Connection, out_dir: Path, season: int | None = None) -> dict[str, str]:
    return export_wide(conn, "player_season", out_dir, season)


def team_season_ranks(conn: sqlite3.Connection, season: int | None = None) -> pd.DataFrame:
    """Rank every team stat within its season: 1 = best (or highest when the stat has no direction)."""
    long = pd.read_sql_query(
        f"""
        SELECT s.season, s.season_type, s.team_id, t.team_name, s.source_system, s.stat_table, s.stat_name,
               d.higher_is_better, s.value
        FROM fact_team_season_stat s
        LEFT JOIN dim_team t ON t.team_id = s.team_id
        LEFT JOIN dim_stat d ON d.entity = 'team' AND d.source_system = s.source_system
                            AND d.stat_table = s.stat_table AND d.stat_name = s.stat_name
        {"WHERE s.season = ?" if season is not None else ""}
        """,
        conn, params=(season,) if season is not None else (),
    )
    if long.empty:
        return long
    group_keys = ["season", "season_type", "source_system", "stat_table", "stat_name"]
    ascending = long["higher_is_better"] == 0  # lower is better -> rank ascending
    high = long.groupby(group_keys)["value"].rank(method="min", ascending=False)
    low = long.groupby(group_keys)["value"].rank(method="min", ascending=True)
    long["rank"] = high.where(~ascending, low).astype(int)
    long["teams"] = long.groupby(group_keys)["value"].transform("count")
    long["direction_known"] = long["higher_is_better"].notna()
    return long.drop(columns=["higher_is_better"]).sort_values([*group_keys, "rank"])


def player_season_percentiles(conn: sqlite3.Connection, season: int | None = None) -> pd.DataFrame:
    """League percentiles for every full-season (split TOT) stat among qualified players.

    Labels, units and definitions are in dim_stat.csv (join on source_system, stat_table, stat_name).
    percentile         rank of the raw value (100 = highest)
    percentile_better  direction-adjusted (100 = best); empty when direction depends on context
    """
    long = pd.read_sql_query(
        f"""
        SELECT s.season, s.season_type, s.player_id, p.player_name, s.team_id, s.source_system, s.stat_table,
               s.stat_name, d.higher_is_better, s.value
        FROM fact_player_season_stat s
        LEFT JOIN dim_player p ON p.player_id = s.player_id
        LEFT JOIN dim_stat d ON d.entity = 'player' AND d.source_system = s.source_system
                            AND d.stat_table = s.stat_table AND d.stat_name = s.stat_name
        WHERE s.split = 'TOT' {"AND s.season = ?" if season is not None else ""}
        """,
        conn, params=(season,) if season is not None else (),
    )
    if long.empty:
        return long

    minutes = []
    for source, (table, stat) in MINUTES_STAT.items():
        rows = long[(long.source_system == source) & (long.stat_table == table) & (long.stat_name == stat)]
        minutes.append(rows[["season", "season_type", "player_id", "source_system", "value"]])
    minutes = pd.concat(minutes).rename(columns={"value": "minutes"})
    long = long.merge(minutes, on=["season", "season_type", "player_id", "source_system"], how="inner")
    long = long[long["minutes"] >= long["season_type"].map(QUALIFY_MINUTES)]

    group = long.groupby(["season", "season_type", "source_system", "stat_table", "stat_name"])["value"]
    long["qualified_players"] = group.transform("count")
    long["percentile"] = (group.rank(pct=True) * 100).round(1)
    lower = (long.groupby(["season", "season_type", "source_system", "stat_table", "stat_name"])["value"]
             .rank(pct=True, ascending=False) * 100).round(1)
    long["percentile_better"] = long["percentile"].where(long["higher_is_better"] == 1)
    long.loc[long["higher_is_better"] == 0, "percentile_better"] = lower
    long["value"] = long["value"].round(4)
    return long.drop(columns=["higher_is_better", "minutes"]).sort_values(
        ["season", "season_type", "source_system", "stat_table", "stat_name", "value"],
        ascending=[True, True, True, True, True, False])


def latest_season(conn: sqlite3.Connection) -> int | None:
    for table in ("fact_player_season_stat", "fact_player_game", "fact_team_season"):
        season = conn.execute(f"SELECT MAX(season) FROM {table}").fetchone()[0]
        if season is not None:
            return int(season)
    return None


def export_tables(db_path: Path | str = DB_PATH, out_dir: Path | str | None = None,
                  season: int | None = None, all_seasons: bool = False) -> dict[str, str]:
    conn = sqlite3.connect(str(db_path))
    if out_dir is None:
        out_dir = CLEAN_DIR / f"season_{season}" if season is not None and not all_seasons else CLEAN_DIR
    if all_seasons:
        season = None
    elif season is None:
        season = latest_season(conn)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exports: dict[str, str] = {}
    try:
        existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        for table in EXPORT_TABLES:
            if table not in existing:
                continue
            scoped = table.startswith(SEASON_SCOPED_PREFIXES)
            df = _read(conn, f"SELECT * FROM {table} {{where}}", season if scoped else None)
            path = out_dir / f"{table}.csv"
            df.to_csv(path, index=False)
            exports[table] = str(path)

        analysis_dir = out_dir / "analysis"
        analysis_dir.mkdir(exist_ok=True)
        for name, sql, alias in (("player_games", PLAYER_GAMES_SQL, "g."), ("team_seasons", TEAM_SEASONS_SQL, "s.")):
            path = analysis_dir / f"{name}.csv"
            _read(conn, sql, season, alias).to_csv(path, index=False)
            exports[f"analysis/{name}"] = str(path)

        for folder in WIDE_EXPORTS:
            exports.update(export_wide(conn, folder, out_dir / folder, season))
        if "dim_stat" in existing:
            path = analysis_dir / "player_season_percentiles.csv"
            player_season_percentiles(conn, season).to_csv(path, index=False)
            exports["analysis/player_season_percentiles"] = str(path)
            path = analysis_dir / "team_season_ranks.csv"
            team_season_ranks(conn, season).to_csv(path, index=False)
            exports["analysis/team_season_ranks"] = str(path)
    finally:
        conn.close()
    return exports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", type=int, help="Export this season to data/clean/season_<N>/.")
    parser.add_argument("--all-seasons", action="store_true", help="Export every season to data/clean/.")
    args = parser.parse_args()
    for name, path in export_tables(season=args.season, all_seasons=args.all_seasons).items():
        print(f"{name:45s} {path}")
