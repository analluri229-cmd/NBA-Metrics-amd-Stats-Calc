"""Extractor behaviour without the network: retries, skips and failure reporting."""
from __future__ import annotations

import pytest

from pipeline.etl.orchestrator import parse_seasons
from pipeline.etl.sources.nba_stats import extract as nba
from pipeline.etl.sources.pulling import NotAvailable, with_retries


def test_parse_seasons_accepts_ranges():
    assert parse_seasons(["2017-2019", "2026", "2018"]) == [2017, 2018, 2019, 2026]


def test_with_retries_recovers_from_transient_errors():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("timeout")
        return "ok"

    assert with_retries(flaky, retries=3, base_delay=0) == "ok" and len(calls) == 3


def test_with_retries_does_not_retry_unavailable():
    calls = []

    def missing():
        calls.append(1)
        raise NotAvailable("404")

    with pytest.raises(NotAvailable):
        with_retries(missing, retries=3, base_delay=0)
    assert len(calls) == 1


class _FakeEndpoint:
    fail_for: set[str] = set()

    def __init__(self, **params):
        self.params = params

    def get_dict(self):
        if self.params.get("pt_measure_type") in self.fail_for:
            raise ConnectionError("stats.nba.com timed out")
        return {"resultSets": [{"name": "x", "headers": ["PLAYER_ID"], "rowSet": []}], "parameters": self.params}


def test_nba_pull_skips_existing_and_reports_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(nba, "_endpoint", lambda path: _FakeEndpoint)
    monkeypatch.setattr(_FakeEndpoint, "fail_for", {"Drives"})
    tables = ["player_season_totals", "player_season_tracking_drives", "player_season_hustle"]
    existing = nba.raw_path(2020, "player_season_totals", out_root=tmp_path)
    existing.parent.mkdir(parents=True)
    existing.write_text("{}")

    report = nba.pull_season(2020, tables=tables, out_root=tmp_path, delay=0, skip_existing=True, retries=2)

    assert report.skipped == [existing] and existing.read_text() == "{}"
    assert [p.name for p in report.written] == ["player_season_hustle.json"]
    assert len(report.failed) == 1 and "tracking_drives" in report.failed[0][0]


def test_nba_pull_playoffs_only_writes_playoff_files(tmp_path, monkeypatch):
    monkeypatch.setattr(nba, "_endpoint", lambda path: _FakeEndpoint)
    report = nba.pull_season(2026, tables=["player_game_log"], season_types=["playoffs"], out_root=tmp_path, delay=0)
    assert [p.name for p in report.written] == ["player_game_log_playoffs.json"]


@pytest.mark.parametrize("values, expected", [
    (["2026"], [2026]), (["2025-26"], [2026]), (["2025-2026"], [2025, 2026]),
    (["2017-2025"], list(range(2017, 2026))), (["2010-2012", "2026"], [2010, 2011, 2012, 2026]),
    (["2010-2012,", "2025-26"], [2010, 2011, 2012, 2026]),
])
def test_parse_seasons_labels_and_ranges(values, expected):
    assert parse_seasons(values) == expected


@pytest.mark.parametrize("bad", [["2025-2017"], ["abc"], ["2025-7"]])
def test_parse_seasons_rejects(bad):
    with pytest.raises(ValueError):
        parse_seasons(bad)
