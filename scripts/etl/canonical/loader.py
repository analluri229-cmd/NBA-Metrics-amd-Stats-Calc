"""Write adapter output into the warehouse.

One raw file is one transaction: its canonical rows and its ``source_manifest``
entry commit together, or the rows roll back and a ``failed`` manifest row is
written instead. A file whose content hash already loaded successfully is
skipped unless ``force`` is set.
"""
from __future__ import annotations

import sqlite3
import traceback
from datetime import datetime, timezone

from .contract import AdapterResult, RawFile, SourceAdapter
from .dates import season_from_date
from .metrics import possessions_used_per_minute, true_shooting
from .resolver import IdResolver
from .schema import ADAPTER_WRITABLE, FACT_TABLES, LOAD_ORDER, SOURCE_PRECEDENCE, STAT_TABLES, TABLES, Table
from .teams import FRANCHISES_BY_ID, dim_team_row

_TEAM_COLUMNS = ("team_id", "opponent_team_id", "team_id_current")
# Long stat tables: source_system is part of the key, so each row has exactly one writer file.
REPLACED_PER_FILE = frozenset(table for table, _, _ in STAT_TABLES)


def _precedence_sql(expr: str) -> str:
    cases = " ".join(f"WHEN '{name}' THEN {rank}" for name, rank in SOURCE_PRECEDENCE.items())
    return f"(CASE {expr} {cases} ELSE 0 END)"


def upsert_sql(table: Table) -> str:
    cols = table.column_names
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = []
    incoming_wins = (
        f"{_precedence_sql('excluded.source_system')} >= {_precedence_sql(f'{table.name}.source_system')}"
    )
    for col in cols:
        if col in table.primary_key:
            continue
        current, incoming = f"{table.name}.{col}", f"excluded.{col}"
        if table.uses_precedence and col in ("source_system", "run_id"):
            updates.append(f"{col} = CASE WHEN {incoming_wins} THEN {incoming} ELSE {current} END")
        elif table.uses_precedence:
            updates.append(
                f"{col} = CASE WHEN {incoming_wins} THEN COALESCE({incoming}, {current}) "
                f"ELSE COALESCE({current}, {incoming}) END"
            )
        elif col in table.fill_only:
            updates.append(f"{col} = COALESCE({current}, {incoming})")
        else:
            updates.append(f"{col} = COALESCE({incoming}, {current})")
    on_conflict = f"DO UPDATE SET {', '.join(updates)}" if updates else "DO NOTHING"  # key-only tables
    return (
        f"INSERT INTO {table.name} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(table.primary_key)}) {on_conflict}"
    )


def insert_ignore_sql(table: Table) -> str:
    cols = table.column_names
    return f"INSERT OR IGNORE INTO {table.name} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"


def _complete(table: Table, row: dict) -> dict:
    unknown = set(row) - set(table.column_names)
    if unknown:
        raise ValueError(f"{table.name}: unknown columns {sorted(unknown)}")
    full = {col: row.get(col) for col in table.column_names}
    missing = [col for col in table.primary_key if full[col] in (None, "")]
    if missing:
        raise ValueError(f"{table.name}: missing key columns {missing} in {row}")
    return full


def _derive(table_name: str, row: dict) -> None:
    if table_name == "fact_player_game":
        if row.get("usage_proxy") is None:
            row["usage_proxy"] = possessions_used_per_minute(row.get("fga"), row.get("fta"), row.get("tov"),
                                                             row.get("minutes"))
        if row.get("efficiency_proxy") is None:
            row["efficiency_proxy"] = true_shooting(row.get("points"), row.get("fga"), row.get("fta"))


def _auto_dimensions(records: dict[str, list[dict]], player_names: dict[str, str]) -> dict[str, list[dict]]:
    """Dimension rows implied by the facts, inserted only if missing."""
    team_ids: set[str] = set()
    date_ids: set[str] = set()
    player_ids: set[str] = set()
    for rows in records.values():
        for row in rows:
            team_ids.update(row[c] for c in _TEAM_COLUMNS if row.get(c) in FRANCHISES_BY_ID)
            if row.get("date_id"):
                date_ids.add(row["date_id"])
            if row.get("player_id"):
                player_ids.add(row["player_id"])
    return {
        "dim_team": [dim_team_row(team_id) for team_id in sorted(team_ids)],
        "dim_date": [
            {"date_id": d, "calendar_date": d, "season": season_from_date(d), "month": int(d[5:7]),
             "year": int(d[:4]), "is_playoff": 0}
            for d in sorted(date_ids)
        ],
        "dim_player": [
            {"player_id": pid, "player_name": player_names.get(pid) or pid} for pid in sorted(player_ids)
        ],
    }


def _count_new_keys(conn: sqlite3.Connection, table: Table, rows: list[dict]) -> int:
    """How many distinct keys in ``rows`` are not in ``table`` yet.

    Looks the batch's keys up through the primary key index, so the cost scales
    with the file being loaded rather than with the size of the warehouse.
    """
    key_columns = table.primary_key
    keys = {tuple(row[c] for c in key_columns) for row in rows}
    temp_columns = ", ".join(f"k{i}" for i in range(len(key_columns)))
    conn.execute("DROP TABLE IF EXISTS temp.load_keys")
    conn.execute(f"CREATE TEMP TABLE load_keys ({temp_columns})")
    conn.executemany(f"INSERT INTO load_keys VALUES ({', '.join('?' for _ in key_columns)})", keys)
    join = " AND ".join(f"t.{c} = k.k{i}" for i, c in enumerate(key_columns))
    existing = conn.execute(f"SELECT COUNT(*) FROM load_keys k JOIN {table.name} t ON {join}").fetchone()[0]
    conn.execute("DROP TABLE temp.load_keys")
    return len(keys) - existing


def load_result(conn: sqlite3.Connection, result: AdapterResult, run_id: str) -> dict[str, dict[str, int]]:
    """Validate and upsert every record in ``result``. Caller owns the transaction."""
    for table_name in result.records:
        if table_name not in ADAPTER_WRITABLE:
            raise ValueError(f"adapter {result.source_name} may not write {table_name}")

    records: dict[str, list[dict]] = {}
    for table_name, rows in result.records.items():
        table = TABLES[table_name]
        prepared = []
        for row in rows:
            row = dict(row)
            if "run_id" in table.column_names:
                row["run_id"] = run_id
            if "source_system" in table.column_names and not row.get("source_system"):
                row["source_system"] = result.source_system
            _derive(table_name, row)
            prepared.append(_complete(table, row))
        records[table_name] = prepared

    records["xref_team"] = [_complete(TABLES["xref_team"], r) for r in result.xref_team]
    records["xref_player"] = [_complete(TABLES["xref_player"], r) for r in result.xref_player]
    records["unresolved_entity"] = [
        _complete(TABLES["unresolved_entity"], {**r, "run_id": run_id}) for r in result.unresolved
    ]

    player_names = {r["player_id"]: r["player_name"] for r in result.xref_player}
    for table_name, rows in _auto_dimensions(records, player_names).items():
        table = TABLES[table_name]
        conn.executemany(insert_ignore_sql(table), [_complete(table, row) for row in rows])

    previous_runs = _previous_runs(conn, result)
    counts: dict[str, dict[str, int]] = {}
    for table_name in LOAD_ORDER:
        rows = records.get(table_name)
        if not rows:
            continue
        inserted = _count_new_keys(conn, TABLES[table_name], rows)
        if table_name in REPLACED_PER_FILE and previous_runs:
            # One source writes each key, so this file's earlier rows are replaced, not merged:
            # a stat the file no longer produces must not linger.
            conn.execute(f"DELETE FROM {table_name} WHERE run_id IN ({', '.join('?' for _ in previous_runs)})",
                         previous_runs)
        conn.executemany(upsert_sql(TABLES[table_name]), rows)
        counts[table_name] = {"inserted": inserted, "updated": len(rows) - inserted}

    # A player that now matches is no longer waiting for review.
    conn.executemany(
        "DELETE FROM unresolved_entity WHERE entity_type = 'player' AND source_name = ? AND source_key = ?",
        [(r["source_name"], r["source_key"]) for r in result.xref_player if r["match_method"] != "fallback"],
    )
    if "fact_lineup_season_stat" in records:
        _drop_orphan_lineups(conn)
    _drop_remapped_players(conn, result)
    conn.execute(
        "UPDATE fact_team_season SET net_rtg = ROUND(off_rtg - def_rtg, 1) "
        "WHERE net_rtg IS NULL AND off_rtg IS NOT NULL AND def_rtg IS NOT NULL"
    )
    return counts


def _drop_orphan_lineups(conn: sqlite3.Connection) -> None:
    """Lineups with no stats left (e.g. rebuilt under a re-mapped member id) are removed."""
    orphan = "lineup_id NOT IN (SELECT DISTINCT lineup_id FROM fact_lineup_season_stat)"
    conn.execute(f"DELETE FROM bridge_lineup_player WHERE {orphan}")
    conn.execute(f"DELETE FROM dim_lineup WHERE {orphan}")


def drop_unreferenced_fallback_players(conn: sqlite3.Connection) -> int:
    """Fallback players (nba_*/name_*) that no table references any more, after a run's remaps."""
    references = " AND ".join(
        f"player_id NOT IN (SELECT player_id FROM {table})"
        for table in ("fact_player_game", "fact_player_season", "fact_player_season_stat",
                      "fact_player_rating_daily", "fact_shot", "xref_player", "bridge_lineup_player")
    )
    with conn:
        return conn.execute(
            "DELETE FROM dim_player WHERE (substr(player_id, 1, 4) = 'nba_' OR substr(player_id, 1, 5) = 'name_') "
            f"AND {references}"
        ).rowcount


def _previous_runs(conn: sqlite3.Connection, result: AdapterResult) -> list[str]:
    """run_ids of earlier successful loads of the same raw file."""
    return [row[0] for row in conn.execute(
        "SELECT run_id FROM source_manifest WHERE source_name = ? AND source_file = ? AND status = 'success'",
        (result.source_name, result.source_file),
    )]


def _drop_remapped_players(conn: sqlite3.Connection, result: AdapterResult) -> None:
    """Remove rows this same raw file wrote earlier under a fallback id that now resolves.

    Only rows from previous loads of this file are removed (matched by run_id); rows
    other files wrote under the old id stay until those files are re-ingested, so a
    partial ``ingest --force`` never deletes data it does not reload.
    """
    if not result.remapped:
        return
    previous_runs = _previous_runs(conn, result)
    if not previous_runs:
        return
    run_filter = f"run_id IN ({', '.join('?' for _ in previous_runs)})"
    player_tables = [name for name in FACT_TABLES if "player_id" in TABLES[name].column_names]
    for old_id in result.remapped:
        for table in player_tables:
            conn.execute(f"DELETE FROM {table} WHERE player_id = ? AND {run_filter}", (old_id, *previous_runs))
        still_used = any(
            conn.execute(f"SELECT 1 FROM {table} WHERE player_id = ? LIMIT 1", (old_id,)).fetchone()
            for table in (*player_tables, "xref_player", "bridge_lineup_player")
        )
        if not still_used:
            conn.execute("DELETE FROM dim_player WHERE player_id = ?", (old_id,))


def refresh_dim_date_seasons(conn: sqlite3.Connection) -> int:
    """Set dim_date.season from the season the sources state for games on that date.

    Dates are first created from the calendar rule (dates.season_from_date); this
    brings them in line with the sources, e.g. the August 2020 bubble games.
    """
    changed = 0
    with conn:
        for table in ("fact_team_game", "fact_player_game"):
            changed += conn.execute(f"""
                UPDATE dim_date SET season = s.season
                FROM (SELECT date_id, MAX(season) AS season FROM {table} GROUP BY date_id) AS s
                WHERE s.date_id = dim_date.date_id AND dim_date.season IS NOT s.season
            """).rowcount
    return changed


def already_loaded(conn: sqlite3.Connection, raw: RawFile) -> bool:
    row = conn.execute(
        "SELECT 1 FROM source_manifest WHERE source_name = ? AND file_sha256 = ? AND status = 'success' LIMIT 1",
        (raw.source_name, raw.sha256),
    ).fetchone()
    return row is not None


def _write_manifest(conn: sqlite3.Connection, raw: RawFile, source_system: str, run_id: str, status: str,
                    counts: dict[str, dict[str, int]] | None = None, result: AdapterResult | None = None,
                    error: str | None = None) -> None:
    counts = counts or {}
    fact_counts = [c for name, c in counts.items() if name in FACT_TABLES]
    conn.execute(
        """
        INSERT INTO source_manifest (
            source_name, run_id, run_timestamp, source_file, rows_inserted, rows_updated, rows_skipped, status,
            source_system, data_type, season, file_sha256, raw_row_count, rows_unresolved, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            raw.source_name, run_id, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), str(raw.path),
            sum(c["inserted"] for c in fact_counts), sum(c["updated"] for c in fact_counts),
            len(result.skipped) if result else 0, status, source_system, raw.data_type, raw.season, raw.sha256,
            result.raw_row_count if result else None, len(result.unresolved) if result else 0, error,
        ),
    )


def ingest_file(conn: sqlite3.Connection, adapter: SourceAdapter, raw: RawFile, force: bool = False,
                resolver: IdResolver | None = None) -> dict:
    """Load one raw file. Pass a shared ``resolver`` when loading many files (see IdResolver.begin_file)."""
    summary = {"source_name": raw.source_name, "data_type": raw.data_type, "season": raw.season,
               "file": str(raw.path)}
    if not force and already_loaded(conn, raw):
        return {**summary, "status": "skipped", "rows_inserted": 0, "rows_updated": 0}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    run_id = f"{raw.source_name}-{stamp}-{raw.sha256[:8]}"
    result: AdapterResult | None = None
    try:
        if resolver is None:
            resolver = IdResolver.from_connection(conn)
        resolver.begin_file()
        result = adapter.parse(raw, resolver)
        result.xref_team = list(resolver.xref_team.values())
        result.xref_player = list(resolver.xref_player.values())
        result.unresolved = list(resolver.unresolved.values())
        result.remapped = dict(resolver.remapped)
        with conn:
            counts = load_result(conn, result, run_id)
            _write_manifest(conn, raw, adapter.source_system, run_id, "success", counts, result)
        resolver.commit_file()
    except Exception as exc:  # recorded in the manifest, reported to the caller
        conn.rollback()
        with conn:
            _write_manifest(conn, raw, adapter.source_system, run_id, "failed", result=result,
                            error=f"{type(exc).__name__}: {exc}")
        return {**summary, "status": "failed", "run_id": run_id, "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}

    fact_counts = [c for name, c in counts.items() if name in FACT_TABLES]
    return {
        **summary, "status": "success", "run_id": run_id,
        "rows_inserted": sum(c["inserted"] for c in fact_counts),
        "rows_updated": sum(c["updated"] for c in fact_counts),
        "rows_skipped": len(result.skipped), "rows_unresolved": len(result.unresolved), "tables": counts,
    }
