"""Shot chart, shot context (defender distance x shot clock) and on/off tables from stats.nba.com."""
from __future__ import annotations

from pipeline.etl.canonical.resolver import IdResolver
from pipeline.etl.sources.nba_stats.adapter import NbaStatsAdapter, stat_table_for
from pipeline.etl.sources.nba_stats.extract import ALL_TABLES, TEAM_REQUEST_TABLES, team_raw_path
from pipeline.etl.sources.registry import ingest

JOKIC = [("jokicni01", "Nikola Jokić")]


def _parse(raw_root, data_type, resolver=None):
    adapter = NbaStatsAdapter()
    raw = next(r for r in adapter.discover(raw_root) if r.data_type == data_type)
    return adapter.parse(raw, resolver or IdResolver(players=JOKIC))


def test_every_defender_distance_and_shot_clock_pair_is_a_table():
    context = [name for name in ALL_TABLES if name.startswith("player_season_shot_context_")]
    assert len(context) == 4 * 7
    assert stat_table_for("player_season_shot_context_very_tight_clock_4_0") == ("shot_context", "very_tight_clock_4_0_")


def test_team_request_tables_are_saved_per_team(tmp_path):
    assert set(TEAM_REQUEST_TABLES) == {"shot_chart", "on_off"}
    assert team_raw_path(2026, "shot_chart", "ORL", "playoffs", tmp_path) == tmp_path / "2026" / "shot_chart" / "ORL_playoffs.json"


def test_shot_chart_rows_carry_game_location_and_result(raw_root):
    shots = _parse(raw_root, "shot_chart").records["fact_shot"]
    assert len(shots) == 6 and {s["player_id"] for s in shots} == {"jokicni01"}
    shot = shots[0]
    assert shot["team_id"] == "DEN" and shot["season"] == 2026 and shot["season_type"] == "regular"
    assert shot["game_id"].startswith(shot["date_id"]) and "DEN" in shot["game_id"]
    assert shot["opponent_team_id"] != "DEN" and shot["opponent_team_id"] in shot["game_id"]
    assert {s["shot_type"] for s in shots} == {"2PT", "3PT"} and {s["made"] for s in shots} <= {0, 1}
    assert all(0 <= s["period_seconds_left"] <= 720 for s in shots)
    assert all(s["zone_basic"] and s["distance_ft"] is not None for s in shots)


def test_shot_context_prefixes_stats_with_the_bin(raw_root):
    rows = _parse(raw_root, "player_season_shot_context_tight_clock_15_7").records["fact_player_season_stat"]
    jokic = {r["stat_name"]: r for r in rows if r["player_id"] == "jokicni01"}
    assert jokic and all(r["stat_table"] == "shot_context" and r["split"] == "TOT" for r in jokic.values())
    assert {"tight_clock_15_7_fga", "tight_clock_15_7_fg_pct", "tight_clock_15_7_fga_frequency"} <= set(jokic)
    assert not {"tight_clock_15_7_gp", "tight_clock_15_7_age"} & set(jokic)


def test_on_off_rows_have_both_sides_per_team(raw_root):
    resolver = IdResolver(players=JOKIC)
    result = _parse(raw_root, "on_off", resolver)
    rows = [r for r in result.records["fact_player_season_stat"] if r["player_id"] == "jokicni01"]
    stats = {r["stat_name"]: r["value"] for r in rows}
    assert {r["split"] for r in rows} == {"DEN"} and {r["stat_table"] for r in rows} == {"on_off"}
    assert stats["on_min"] > stats["off_min"] > 0
    assert stats["on_fga"] > 0 and "on_vs_player_id" not in stats
    # on/off lists players as "Jokić, Nikola"; only the flipped name matches by name
    assert resolver.xref_player[("nba_stats", "203999")]["player_name"] == "Nikola Jokić"
    assert resolver.xref_player[("nba_stats", "203999")]["match_method"] == "name"


def test_new_tables_load_into_the_warehouse(conn, raw_root):
    summaries = ingest(conn, ["bbref_player_season", "nba_stats"], raw_root=raw_root)
    assert all(s["status"] == "success" for s in summaries), [s.get("error") for s in summaries]
    assert conn.execute("SELECT COUNT(*) FROM fact_shot WHERE player_id = 'jokicni01'").fetchone() == (6,)
    assert conn.execute("SELECT COUNT(*) FROM fact_player_season_stat WHERE stat_table = 'on_off' "
                        "AND player_id = 'jokicni01'").fetchone()[0] > 0
    ingest(conn, ["nba_stats"], raw_root=raw_root, force=True)  # reload replaces, never duplicates
    assert conn.execute("SELECT COUNT(*) FROM fact_shot").fetchone() == (6,)
