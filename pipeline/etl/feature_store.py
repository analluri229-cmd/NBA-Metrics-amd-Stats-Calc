from __future__ import annotations

import sqlite3
from pathlib import Path

from pipeline.etl.paths import DB_PATH

FEATURE_SQL = """
CREATE TABLE IF NOT EXISTS feature_player_daily (
    feature_id TEXT PRIMARY KEY,
    player_id TEXT,
    team_id TEXT,
    season INTEGER,
    date_id TEXT,
    points REAL,
    assists REAL,
    rebounds REAL,
    usage_proxy REAL,
    efficiency_proxy REAL,
    rolling_3_game_points REAL,
    rolling_5_game_points REAL,
    home_away TEXT,
    source_system TEXT
);
"""


def initialize_feature_store(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(FEATURE_SQL)
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = initialize_feature_store()
    print(f"Feature store initialized: {DB_PATH}")
    conn.close()
