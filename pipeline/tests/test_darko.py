"""DARKO snapshots: decoding, date selection, parsing and loading.

The fixture keeps real player ids and names but synthetic ratings: DARKO data is not republished.
"""
from __future__ import annotations

import json

from pipeline.etl.canonical.resolver import IdResolver
from pipeline.etl.sources.darko.adapter import DarkoAdapter
from pipeline.etl.sources.darko.extract import game_dates, snapshot_dates
from pipeline.etl.sources.darko.page_data import unflatten
from pipeline.etl.sources.registry import ingest


def _parse(raw_root, resolver=None):
    adapter = DarkoAdapter()
    raw = adapter.discover(raw_root)[0]
    return adapter.parse(raw, resolver or IdResolver())


def _stats(result, player_id):
    return {r["stat_name"]: r for r in result.records["fact_player_rating_daily"] if r["player_id"] == player_id}


def test_unflatten_resolves_shared_references_and_specials():
    values = [{"a": 1, "b": 1, "c": 3, "d": -1}, [2, 2], "x", ["Date", "2026-01-15T00:00:00.000Z"]]
    assert unflatten(values) == {"a": ["x", "x"], "b": ["x", "x"], "c": "2026-01-15T00:00:00.000Z", "d": None}


def test_snapshot_dates_keeps_spacing_and_season_end_points():
    dates = ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-09", "2026-01-10", "2026-04-12", "2026-06-13"]
    assert snapshot_dates(dates, every_days=7, keep=("2026-04-12",)) == \
        ["2026-01-01", "2026-01-09", "2026-04-12", "2026-06-13"]
    assert snapshot_dates(dates, every_days=1) == dates


def test_game_dates_come_from_the_team_game_log(raw_root):
    dates, last_regular = game_dates(2026, raw_root)
    assert dates == sorted(set(dates)) and last_regular in dates


def test_snapshot_rows_are_keyed_by_the_data_date(raw_root):
    resolver = IdResolver(players=[("jokicni01", "Nikola Jokić"), ("hardeja01", "James Harden")])
    result = _parse(raw_root, resolver)
    jokic = _stats(result, "jokicni01")
    assert jokic["dpm"]["value"] == 5.0 and jokic["dpm"]["date_id"] == "2026-01-15"
    assert jokic["dpm"]["season"] == 2026 and jokic["dpm"]["team_id"] == "DEN"
    assert {"o_dpm", "d_dpm", "box_dpm", "on_off_dpm", "x_minutes"} <= set(jokic)
    assert not {"nba_id", "tm_id", "_rank", "season"} & set(jokic)
    assert _stats(result, "hardeja01")["dpm"]["team_id"] == "LAC"


def test_players_resolve_through_the_nba_stats_person_id(raw_root):
    resolver = IdResolver(xref={("nba_stats", "203999"): ("jokicni01", "name")})
    result = _parse(raw_root, resolver)
    assert _stats(result, "jokicni01")
    assert _stats(result, "nba_1641705")  # not in the warehouse yet: fallback id, queued for review
    assert any(u["source_key"] == "1641705" for u in result.unresolved + list(resolver.unresolved.values()))


def _flatten(root) -> list:
    """devalue-encode ``root`` (the inverse of unflatten, without sharing)."""
    values: list = []

    def encode(value) -> int:
        if value is None:
            return -1
        index = len(values)
        values.append(None)
        if isinstance(value, dict):
            values[index] = {key: encode(item) for key, item in value.items()}
        elif isinstance(value, list):
            values[index] = [encode(item) for item in value]
        else:
            values[index] = value
        return index

    encode(root)
    return values


def test_rating_columns_relative_to_today_are_dropped(raw_root):
    # Historical snapshots add now_dpm/since_dpm: the player's rating today and the change since.
    path = raw_root / "darko" / "2026" / "dpm_2026-01-15.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = unflatten(payload["nodes"][1]["data"])
    players = data["players"]
    players["keys"].append("now_dpm")
    players["values"].append([9.9] * len(players["values"][0]))
    payload["nodes"][1]["data"] = _flatten(data)
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _parse(raw_root)
    assert result.records["fact_player_rating_daily"]
    assert not any(r["stat_name"] == "now_dpm" for r in result.records["fact_player_rating_daily"])


def test_darko_loads_after_nba_stats_and_reloads_idempotently(conn, raw_root):
    summaries = ingest(conn, ["bbref_player_season", "nba_stats", "darko"], raw_root=raw_root)
    assert all(s["status"] == "success" for s in summaries), [s.get("error") for s in summaries]
    rows = conn.execute("SELECT COUNT(*) FROM fact_player_rating_daily").fetchone()[0]
    dpm = conn.execute("SELECT value FROM fact_player_rating_daily WHERE player_id = 'jokicni01' "
                       "AND date_id = '2026-01-15' AND stat_name = 'dpm'").fetchone()
    assert rows > 0 and dpm == (5.0,)
    ingest(conn, ["darko"], raw_root=raw_root, force=True)
    assert conn.execute("SELECT COUNT(*) FROM fact_player_rating_daily").fetchone()[0] == rows
