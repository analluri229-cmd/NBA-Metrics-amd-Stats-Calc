from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.etl.canonical.schema import DERIVED_TABLES, TABLES, schema_sql
from scripts.etl.paths import DB_PATH, PROJECT_ROOT  # noqa: F401  (re-exported for older imports)

SCHEMA_SQL = schema_sql()


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _recreate_changed_derived_tables(conn: sqlite3.Connection) -> None:
    """Derived tables (rebuilt every run) are dropped when their columns or key changed."""
    for name in DERIVED_TABLES:
        info = conn.execute(f"PRAGMA table_info({name})").fetchall()
        columns = tuple(row[1] for row in info)
        key = tuple(row[1] for row in sorted(info, key=lambda row: row[5]) if row[5])
        if info and (columns != TABLES[name].column_names or key != TABLES[name].primary_key):
            conn.execute(f"DROP TABLE {name}")
            conn.execute(TABLES[name].ddl())


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    """Bring a warehouse created by an older schema up to date (additive only)."""
    _recreate_changed_derived_tables(conn)
    for table in TABLES.values():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table.name})")}
        for name, sql_type in table.columns:
            if name not in existing:
                # SQLite cannot add NOT NULL columns without a default.
                conn.execute(f"ALTER TABLE {table.name} ADD COLUMN {name} {sql_type.replace('NOT NULL', '')}")


def initialize_database(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect(db_path)
    conn.executescript(SCHEMA_SQL)
    _add_missing_columns(conn)
    conn.commit()
    return conn


def ensure_schema(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    return initialize_database(db_path)


if __name__ == "__main__":
    conn = ensure_schema()
    print(f"Warehouse ready: {DB_PATH}")
    conn.close()
