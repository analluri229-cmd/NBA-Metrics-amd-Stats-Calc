from __future__ import annotations

import pytest

from scripts.etl.canonical.contract import AdapterResult, RawFile
from scripts.etl.canonical.loader import ingest_file
from scripts.etl.canonical.schema import FACT_TABLES
from scripts.etl.sources.registry import ADAPTERS, ingest


def _count(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


def test_reingest_is_skipped_and_force_is_idempotent(conn, raw_root):
    first = ingest(conn, raw_root=raw_root)
    assert first and all(s["status"] == "success" for s in first), [s.get("error") for s in first]
    counts = {t: _count(conn, f"SELECT COUNT(*) FROM {t}") for t in FACT_TABLES}

    second = ingest(conn, raw_root=raw_root)
    assert {s["status"] for s in second} == {"skipped"}

    forced = ingest(conn, raw_root=raw_root, force=True)
    assert all(s["status"] == "success" for s in forced)
    assert {t: _count(conn, f"SELECT COUNT(*) FROM {t}") for t in FACT_TABLES} == counts


def test_every_fact_row_traces_to_a_successful_manifest_run(conn, raw_root):
    ingest(conn, raw_root=raw_root)
    for table in FACT_TABLES:
        orphans = _count(conn, f"""
            SELECT COUNT(*) FROM {table} f
            WHERE f.run_id IS NULL OR f.run_id NOT IN (SELECT run_id FROM source_manifest WHERE status = 'success')""")
        assert orphans == 0, table


def test_manifest_records_file_metadata(conn, raw_root):
    ingest(conn, ["bbref_team_season"], raw_root=raw_root)
    rows = conn.execute("SELECT data_type, season, file_sha256, raw_row_count, status FROM source_manifest").fetchall()
    assert len(rows) == 4
    assert all(season == 2026 and len(sha) == 64 and n == 3 and status == "success"
               for _, season, sha, n, status in rows)


def test_nba_stats_beats_legacy_for_the_same_game(conn, raw_root):
    ingest(conn, raw_root=raw_root)
    row = conn.execute("""
        SELECT points, source_system FROM fact_player_game
        WHERE player_id = 'jokicni01' AND date_id = (SELECT MIN(date_id) FROM fact_player_game
                                                     WHERE player_id = 'jokicni01')""").fetchone()
    assert row == (21.0, "nba_stats")  # the legacy fixture says 1 point on the same date


def test_lower_precedence_source_never_overwrites(conn, raw_root):
    ingest(conn, ["nba_stats"], raw_root=raw_root)
    before = conn.execute("SELECT points, source_system FROM fact_player_game WHERE player_id = 'nba_203999' "
                          "OR player_id = 'jokicni01' ORDER BY date_id LIMIT 1").fetchone()
    ingest(conn, ["legacy_sample"], raw_root=raw_root)
    after = conn.execute("SELECT points, source_system FROM fact_player_game WHERE player_id = 'nba_203999' "
                         "OR player_id = 'jokicni01' ORDER BY date_id LIMIT 1").fetchone()
    assert before == after


def test_fallback_player_is_remapped_when_bbref_arrives(conn, raw_root):
    ingest(conn, ["nba_stats"], raw_root=raw_root)  # no bbref slugs yet -> nba_<id>
    assert _count(conn, "SELECT COUNT(*) FROM fact_player_season_stat WHERE player_id LIKE 'nba_%'") > 0

    ingest(conn, ["bbref_player_season"], raw_root=raw_root)
    ingest(conn, ["nba_stats"], raw_root=raw_root, force=True)
    remaining = {r[0] for r in conn.execute("SELECT DISTINCT player_id FROM fact_player_season_stat "
                                            "WHERE player_id LIKE 'nba_%'")}
    assert remaining == {"nba_1642380"}  # only Adama Bal, who is not in the bbref fixture
    assert _count(conn, "SELECT COUNT(*) FROM dim_player WHERE player_id = 'nba_203999'") == 0
    assert _count(conn, "SELECT COUNT(*) FROM unresolved_entity WHERE source_key = '203999'") == 0


def test_remap_only_removes_rows_of_the_reloaded_file(conn, raw_root):
    """Forcing one file must not delete rows other files wrote under the same fallback id."""
    ingest(conn, ["nba_stats"], raw_root=raw_root)  # Jokic loads as nba_203999 in every nba file
    games_before = _count(conn, "SELECT COUNT(*) FROM fact_player_game WHERE player_id = 'nba_203999'")
    assert games_before > 0

    ingest(conn, ["bbref_player_season"], raw_root=raw_root)
    totals = next(r for r in ADAPTERS["nba_stats"].discover(raw_root) if r.data_type == "player_season_totals")
    ingest_file(conn, ADAPTERS["nba_stats"], totals, force=True)  # only the totals file is reloaded

    assert _count(conn, "SELECT COUNT(*) FROM fact_player_season_stat WHERE player_id = 'nba_203999' "
                        "AND stat_table = 'totals'") == 0
    assert _count(conn, "SELECT COUNT(*) FROM fact_player_season_stat WHERE player_id = 'jokicni01' "
                        "AND stat_table = 'totals' AND source_system = 'nba_stats'") > 0
    # The game log was not reloaded, so its rows are still there under the old id.
    assert _count(conn, "SELECT COUNT(*) FROM fact_player_game WHERE player_id = 'nba_203999'") == games_before


def test_dim_date_season_follows_the_sources(conn, raw_root):
    from scripts.etl.canonical.loader import refresh_dim_date_seasons

    ingest(conn, ["nba_stats"], raw_root=raw_root)
    date_id = conn.execute("SELECT MIN(date_id) FROM fact_team_game").fetchone()[0]
    conn.execute("UPDATE dim_date SET season = 1999 WHERE date_id = ?", (date_id,))
    assert refresh_dim_date_seasons(conn) == 1
    assert conn.execute("SELECT season FROM dim_date WHERE date_id = ?", (date_id,)).fetchone()[0] == 2026


class _BrokenAdapter:
    source_name = "broken"
    source_system = "legacy_sample"

    def discover(self, raw_root):
        return []

    def parse(self, raw, resolver):
        result = AdapterResult("broken", "legacy_sample", "x", 2026, str(raw.path))
        result.add("dim_team", {"team_id": "ZZZ", "team_name": "Nowhere"})
        result.add("fact_player_game", {"player_game_id": "x", "player_id": "p", "not_a_column": 1})
        return result


def test_failed_file_rolls_back_and_is_recorded(conn, tmp_path):
    path = tmp_path / "broken.csv"
    path.write_text("x\n1\n")
    summary = ingest_file(conn, _BrokenAdapter(), RawFile.from_path(path, "broken", "x", 2026))
    assert summary["status"] == "failed" and "not_a_column" in summary["error"]
    assert _count(conn, "SELECT COUNT(*) FROM dim_team WHERE team_id = 'ZZZ'") == 0
    status, error = conn.execute("SELECT status, error FROM source_manifest WHERE source_name = 'broken'").fetchone()
    assert status == "failed" and "not_a_column" in error


def test_unknown_source_is_rejected(conn):
    with pytest.raises(ValueError):
        ingest(conn, ["not_a_source"])


def test_registry_order_puts_bbref_first():
    assert list(ADAPTERS)[:3] == ["bbref_team_season", "bbref_player_season", "bbref_web"]


def test_lineups_load_with_key_only_bridge_table(conn, raw_root):
    summaries = ingest(conn, ["bbref_player_season", "nba_stats"], raw_root=raw_root)
    assert all(s["status"] == "success" for s in summaries), [s.get("error") for s in summaries]
    lineups = _count(conn, "SELECT COUNT(*) FROM dim_lineup")
    assert lineups == 3 and _count(conn, "SELECT COUNT(*) FROM bridge_lineup_player") == 15
    ingest(conn, ["nba_stats"], raw_root=raw_root, force=True)  # reloading keeps the bridge unique
    assert _count(conn, "SELECT COUNT(*) FROM bridge_lineup_player") == 15


def test_reloaded_file_replaces_its_long_table_rows(conn, raw_root):
    ingest(conn, ["nba_stats"], raw_root=raw_root)
    run = conn.execute("SELECT run_id FROM source_manifest WHERE data_type = 'team_season_hustle'").fetchone()[0]
    conn.execute("INSERT INTO fact_team_season_stat VALUES (2026, 'regular', 'DEN', 'nba_stats', 'hustle', "
                 "'stat_the_source_dropped', 1.0, ?)", (run,))
    conn.commit()
    ingest(conn, ["nba_stats"], raw_root=raw_root, force=True)
    assert _count(conn, "SELECT COUNT(*) FROM fact_team_season_stat WHERE stat_name = 'stat_the_source_dropped'") == 0
    assert _count(conn, "SELECT COUNT(*) FROM fact_team_season_stat WHERE stat_table = 'hustle'") > 0
