"""pipeline/settings.py: defaults validate, bad values are rejected by name, current_season rolls over Nov 1."""
from __future__ import annotations

from datetime import date

import pytest

from pipeline import settings
from pipeline.settings import SettingsError, current_season, validate


def test_defaults_are_valid():
    validate()


def test_current_season_switches_on_nov_1(monkeypatch):
    monkeypatch.setattr(settings, "CURRENT_SEASON", None)
    assert current_season(date(2026, 10, 31)) == 2026
    assert current_season(date(2026, 11, 1)) == 2027
    monkeypatch.setattr(settings, "CURRENT_SEASON", 2025)
    assert current_season(date(2026, 11, 1)) == 2025


@pytest.mark.parametrize("name, value, words", [
    ("SEASON_TYPE", "Both", "SEASON_TYPE"),
    ("BBREF_DELAY_SECONDS", 2, "BBREF_DELAY_SECONDS"),
    ("QUALIFY_MINUTES", {"regular": 0, "playoffs": 100}, "QUALIFY_MINUTES"),
    ("SEASONS", range(1990, 2000), "1997"),
    ("DEFAULT_SOURCES", ("darko", "nba_stats"), "after nba_stats"),
    ("DEFAULT_SOURCES", ("nba_stats", "espn"), "espn"),
    ("DARKO_EVERY_DAYS", 0, "DARKO_EVERY_DAYS"),
    ("NBA_STATS_TABLES", ("not_a_table",), "not_a_table"),
])
def test_validate_rejects_bad_values(monkeypatch, name, value, words):
    monkeypatch.setattr(settings, name, value)
    with pytest.raises(SettingsError, match=words):
        validate()


def test_validate_rejects_string_sources(monkeypatch):
    monkeypatch.setattr(settings, "DEFAULT_SOURCES", "nba_stats")
    with pytest.raises(SettingsError, match="trailing comma"):
        validate()
