"""pull --source bbref_team: writes the four team/opponent CSVs the bbref_team_season adapter reads."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.etl.canonical.resolver import IdResolver
from pipeline.etl.sources.basketball_reference.team_extract import pull_team_tables
from pipeline.etl.sources.basketball_reference.team_season import TeamSeasonAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "pages" / "NBA_2026_team.html"
NAMES = {"team_totals_2026.csv", "opponent_totals_2026.csv", "team_per_100_poss_2026.csv",
         "opponent_per_100_poss_2026.csv"}


def _page(season: int) -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_team_pull_writes_four_csvs(tmp_path):
    report = pull_team_tables(2026, out_root=tmp_path, excel=False, fetch_page=_page)

    assert {p.name for p in report.written} == NAMES
    for name in NAMES:
        df = pd.read_csv(tmp_path / name)
        assert len(df) == 2
        denver = df[df["Team"] == "Denver Nuggets"].iloc[0]
        assert bool(denver["Playoffs"]) is True
        assert not df["Team"].str.contains(r"\*").any()


def test_team_pull_output_ingests(tmp_path):
    pull_team_tables(2026, out_root=tmp_path, excel=False, fetch_page=_page)

    found = TeamSeasonAdapter().discover(tmp_path)
    assert {r.path.name for r in found} == NAMES
    for raw in found:
        result = TeamSeasonAdapter().parse(raw, IdResolver())
        assert result.records and not result.unresolved


def test_team_pull_skip_existing_skips_fetch(tmp_path):
    for name in NAMES:
        (tmp_path / name).write_text("Season,Team\n")

    def fail(season: int) -> str:
        raise AssertionError("page fetched although every file exists")

    report = pull_team_tables(2026, out_root=tmp_path, excel=False, skip_existing=True, fetch_page=fail)

    assert len(report.skipped) == 4 and report.written == []


def test_team_pull_excel_optional(tmp_path):
    pull_team_tables(2026, out_root=tmp_path, excel_dir=tmp_path / "tableau", excel=True, fetch_page=_page)

    book = tmp_path / "tableau" / "team_stats_2026.xlsx"
    assert "All_Stats" in pd.ExcelFile(book).sheet_names


def test_cli_pulls_each_season_with_bbref_delay(monkeypatch):
    from pipeline import settings
    from pipeline.etl import orchestrator
    from pipeline.etl.sources.basketball_reference import team_extract
    from pipeline.etl.sources.pulling import PullReport

    calls, slept = [], []
    monkeypatch.setattr(team_extract, "pull_team_tables",
                        lambda season, skip_existing=False: calls.append((season, skip_existing)) or PullReport())
    monkeypatch.setattr(team_extract.time, "sleep", slept.append)
    monkeypatch.setattr(settings, "BBREF_DELAY_SECONDS", 5)

    assert orchestrator.main(["pull", "--source", "bbref_team", "--season", "2025-2026", "--skip-existing"]) == 0
    assert calls == [(2025, True), (2026, True)] and slept == [5]


def test_team_pull_reports_locked_workbook(tmp_path, monkeypatch):
    from pipeline.etl.sources.basketball_reference import team_extract

    def locked(results, path):
        raise PermissionError(f"[Errno 13] Permission denied: '{path}'")
    monkeypatch.setattr(team_extract, "write_workbook", locked)

    report = pull_team_tables(2026, out_root=tmp_path, excel_dir=tmp_path / "tableau", excel=True, fetch_page=_page)

    assert {p.name for p in report.written} == NAMES
    assert len(report.failed) == 1 and "close it" in report.failed[0][1]
