"""Extractors, exporter and CLI read pipeline/settings.py at call time."""
from __future__ import annotations

import pytest

from pipeline import settings
from pipeline.etl.export_csvs import player_season_percentiles
from pipeline.etl.orchestrator import build_parser, main, run_pipeline
from pipeline.etl.sources.darko import extract as darko
from pipeline.etl.sources.nba_stats import extract as nba
from pipeline.etl.sources.pulling import PullReport
from pipeline.etl.warehouse import connect


class _FakeEndpoint:
    def __init__(self, **params):
        self.params = params

    def get_dict(self):
        return {"resultSets": [{"name": "x", "headers": ["PLAYER_ID"], "rowSet": []}], "parameters": self.params}


def test_nba_pull_uses_settings_delay(tmp_path, monkeypatch):
    monkeypatch.setattr(nba, "_endpoint", lambda path: _FakeEndpoint)
    monkeypatch.setattr(settings, "NBA_STATS_DELAY_SECONDS", 0.25)
    slept: list[float] = []
    monkeypatch.setattr(nba.time, "sleep", slept.append)

    nba.pull_season(2020, tables=["player_season_totals", "player_season_hustle"], out_root=tmp_path)

    assert slept == [0.25]


def test_nba_pull_uses_settings_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(nba, "_endpoint", lambda path: _FakeEndpoint)
    monkeypatch.setattr(nba, "pull_team_tables", lambda *a, **k: PullReport())
    monkeypatch.setattr(settings, "NBA_STATS_TABLES", ("player_season_totals",))

    report = nba.pull_season(2020, out_root=tmp_path, delay=0)

    assert [p.name for p in report.written] == ["player_season_totals.json"]


def test_percentiles_use_settings_qualify_minutes(tmp_path, raw_root, monkeypatch):
    db = tmp_path / "warehouse.db"
    run_pipeline(db, raw_root=raw_root, export_dir=tmp_path / "clean")
    conn = connect(db)
    try:
        monkeypatch.setattr(settings, "QUALIFY_MINUTES", {"regular": 1, "playoffs": 1})
        assert not player_season_percentiles(conn).empty
        monkeypatch.setattr(settings, "QUALIFY_MINUTES", {"regular": 10**6, "playoffs": 10**6})
        assert player_season_percentiles(conn).empty
    finally:
        conn.close()


def test_cli_season_type_defaults_to_settings(monkeypatch):
    monkeypatch.setattr(settings, "SEASON_TYPE", "playoffs")
    assert build_parser().parse_args(["pull", "--source", "nba_stats"]).season_type == "playoffs"


def test_main_rejects_invalid_settings(monkeypatch):
    monkeypatch.setattr(settings, "SEASON_TYPE", "x")
    with pytest.raises(settings.SettingsError):
        main(["features"])


def test_darko_pull_without_game_logs_reports_failure(tmp_path):
    report = darko.pull_season(2019, raw_root=tmp_path, out_root=tmp_path / "darko")

    assert len(report.failed) == 1 and "pull nba_stats" in report.failed[0][1]
    assert report.written == []
