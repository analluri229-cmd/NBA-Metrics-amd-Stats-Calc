"""Dimension upsert helpers (kept for existing imports) and canonical team seeding."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .canonical.dates import season_from_date
from .canonical.loader import upsert_sql
from .canonical.schema import TABLES
from .canonical.teams import FRANCHISES, dim_team_row
from .warehouse import DB_PATH, ensure_schema


def _upsert(conn: sqlite3.Connection, table: str, row: dict) -> None:
    columns = TABLES[table].column_names
    conn.execute(upsert_sql(TABLES[table]), {col: row.get(col) for col in columns})


def upsert_player(conn: sqlite3.Connection, player_id: str, player_name: str, team_id: str | None = None) -> None:
    _upsert(conn, "dim_player", {"player_id": player_id, "player_name": player_name, "team_id_current": team_id})


def upsert_team(conn: sqlite3.Connection, team_id: str, team_name: str, abbreviation: str | None = None) -> None:
    _upsert(conn, "dim_team", {"team_id": team_id, "team_name": team_name, "abbreviation": abbreviation})


def upsert_date(conn: sqlite3.Connection, date_str: str, season: int | None = None) -> None:
    _upsert(conn, "dim_date", {
        "date_id": date_str, "calendar_date": date_str,
        "season": season if season is not None else season_from_date(date_str),
        "month": int(date_str[5:7]), "year": int(date_str[:4]),
    })


def seed_teams(conn: sqlite3.Connection) -> int:
    """Load all 30 franchises (name, city, conference, division) into dim_team."""
    for franchise in FRANCHISES:
        _upsert(conn, "dim_team", dim_team_row(franchise.team_id))
    return len(FRANCHISES)


def apply_canonical_mapping(db_path: Path | str = DB_PATH) -> dict[str, int]:
    conn = ensure_schema(db_path)
    with conn:
        teams = seed_teams(conn)
    conn.close()
    return {"teams": teams}


if __name__ == "__main__":
    print(apply_canonical_mapping())
