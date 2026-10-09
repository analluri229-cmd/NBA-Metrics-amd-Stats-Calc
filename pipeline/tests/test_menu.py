"""python -m pipeline: answers become orchestrator argv lists; nothing touches the network."""
from __future__ import annotations

import pytest

from pipeline import menu, settings
from pipeline.etl.sources.nba_stats.extract import ALL_TABLES, TEAM_REQUEST_TABLES, raw_path, team_raw_path
from pipeline.etl.canonical.teams import FRANCHISES


def answers(*xs):
    queue = list(xs)

    def ask(question):
        if not queue:
            raise AssertionError(f"unexpected question: {question}")
        return queue.pop(0)
    return ask


class Recorder(list):
    def __call__(self, argv):
        self.append(list(argv))
        return 0


class Said(list):
    def __call__(self, text):
        self.append(str(text))

    def has(self, words):
        return any(words in line for line in self)


@pytest.fixture(autouse=True)
def no_real_pipeline(monkeypatch):
    """A menu test must never reach the real orchestrator (network pulls, real warehouse, data/clean)."""
    def refuse(argv=None):
        raise AssertionError(f"real orchestrator called with {argv}")
    monkeypatch.setattr("pipeline.etl.orchestrator.main", refuse)


@pytest.fixture
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "RAW_DIR", tmp_path)
    monkeypatch.setattr(settings, "current_season", lambda today=None: 2026)
    monkeypatch.setattr(settings, "DEFAULT_SOURCES", ("nba_stats", "bbref", "bbref_team", "darko"))
    monkeypatch.setattr(settings, "SEASON_TYPE", "both")
    monkeypatch.setattr(settings, "EXPORT_AFTER_RUN", False)
    monkeypatch.setattr(settings, "BBREF_WITH_WEB_SCRAPER", False)
    return tmp_path


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")


def _all_nba_files(raw, season, season_type="regular"):
    for table in ALL_TABLES:
        _touch(raw_path(season, table, season_type, raw / "nba_stats"))
    for table in TEAM_REQUEST_TABLES:
        for franchise in FRANCHISES:
            _touch(team_raw_path(season, table, franchise.team_id, season_type, raw / "nba_stats"))


def _run(ask, run, say=None):
    return menu.run_menu(ask=ask, say=Said() if say is None else say, run=run, is_tty=lambda: True)


def test_pull_argv_nba_stats():
    assert menu.pull_argv("nba_stats", [2017, 2018], "both", True) == [
        "pull", "--source", "nba_stats", "--season", "2017", "2018", "--season-type", "both", "--skip-existing"]
    assert menu.pull_argv("bbref", [2020], "both", False) == ["pull", "--source", "bbref", "--season", "2020"]


def test_update_current_season_always_refreshes(raw):
    _all_nba_files(raw, 2026)
    run = Recorder()

    assert _run(answers("1", "", "n", "q"), run) == 0

    assert [argv[2] for argv in run] == ["nba_stats", "bbref", "bbref_team", "darko"]
    assert run[0] == menu.pull_argv("nba_stats", [2026], "both", False)
    assert "--skip-existing" in run[3]


def test_backfill_partial_uses_skip_existing(raw):
    _touch(raw_path(2018, "player_season_totals", "regular", raw / "nba_stats"))
    run = Recorder()

    assert _run(answers("2", "2018", "nba_stats", "regular", "", "n", "q"), run) == 0

    assert run == [menu.pull_argv("nba_stats", [2018], "regular", True)]


def test_backfill_all_present_defaults_to_skip(raw):
    _all_nba_files(raw, 2018)
    run = Recorder()
    said = Said()

    assert _run(answers("2", "2018", "nba_stats", "regular", "", "q"), run, said) == 0

    assert run == [] and said.has("already")


def test_backfill_load_and_export(raw):
    run = Recorder()

    assert _run(answers("2", "2018", "bbref", "regular", "", "", "y", "q"), run) == 0

    assert run == [menu.pull_argv("bbref", [2018], "regular", True), ["run", "--export"]]


def test_darko_without_game_logs_is_skipped(raw):
    run = Recorder()
    said = Said()

    assert _run(answers("4", "2019", "q"), run, said) == 0

    assert run == [] and said.has("pull nba_stats")


def test_export_choices(raw):
    run = Recorder()
    assert _run(answers("6", "3", "q"), run) == 0
    assert run == [["export", "--all-seasons"]]


def test_menu_without_tty_prints_help():
    run, said = Recorder(), Said()
    assert menu.run_menu(ask=answers(), say=said, run=run, is_tty=lambda: False) == 0
    assert said.has("pull") and run == []


def test_menu_cancel_exits_cleanly(raw):
    def eof(question):
        raise EOFError
    said = Said()
    assert _run(eof, Recorder(), said) == 1
    assert said.has("Cancelled.")


def test_menu_reports_invalid_settings(monkeypatch):
    monkeypatch.setattr(settings, "SEASON_TYPE", "x")
    said = Said()
    assert menu.run_menu(ask=answers(), say=said, run=Recorder(), is_tty=lambda: True) == 2
    assert said.has("SEASON_TYPE")


class _Stream:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


@pytest.mark.parametrize("stdin, stdout, expected", [(True, True, True), (True, False, False), (False, True, False)])
def test_interactive_needs_console_in_and_out(monkeypatch, stdin, stdout, expected):
    # Windows reports NUL as a console, so stdin alone can't tell a script from a person.
    monkeypatch.setattr(menu.sys, "stdin", _Stream(stdin))
    monkeypatch.setattr(menu.sys, "stdout", _Stream(stdout))
    assert menu.interactive() is expected
