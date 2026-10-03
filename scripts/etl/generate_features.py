"""Build feature_player_daily from the canonical fact_player_game table only."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from scripts.etl.feature_store import initialize_feature_store
from scripts.etl.paths import DB_PATH

FEATURE_TABLE = "feature_player_daily"
FEATURE_COLUMNS = [
    "feature_id", "player_id", "team_id", "season", "date_id", "points", "assists", "rebounds", "usage_proxy",
    "efficiency_proxy", "rolling_3_game_points", "rolling_5_game_points", "home_away", "source_system",
]


def load_player_games(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM fact_player_game", conn)
    return df.sort_values(["player_id", "date_id"], kind="stable").reset_index(drop=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)
    out = df.copy()
    points = out.groupby("player_id")["points"]
    out["rolling_3_game_points"] = points.transform(lambda s: s.rolling(3, min_periods=1).mean())
    out["rolling_5_game_points"] = points.transform(lambda s: s.rolling(5, min_periods=1).mean())
    out["feature_id"] = out["player_game_id"].astype(str)
    return out[FEATURE_COLUMNS]


def write_features(conn: sqlite3.Connection, features: pd.DataFrame) -> int:
    """Replace the feature table: features are fully derived, so a rebuild is deterministic."""
    rows = features.astype(object).where(features.notna(), None).itertuples(index=False, name=None)
    with conn:
        conn.execute(f"DELETE FROM {FEATURE_TABLE}")
        conn.executemany(
            f"INSERT INTO {FEATURE_TABLE} ({', '.join(FEATURE_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in FEATURE_COLUMNS)})",
            list(rows),
        )
    return len(features)


def generate_features(db_path: Path | str = DB_PATH) -> int:
    conn = initialize_feature_store(db_path)
    try:
        return write_features(conn, build_features(load_player_games(conn)))
    finally:
        conn.close()


if __name__ == "__main__":
    print({"features_inserted": generate_features()})
