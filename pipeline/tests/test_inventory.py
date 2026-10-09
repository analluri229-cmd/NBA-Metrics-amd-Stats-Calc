"""What each source already has on disk, per season and season type."""
from __future__ import annotations

from pipeline.etl.sources.inventory import inventory
from pipeline.etl.sources.nba_stats.extract import ALL_TABLES, TEAM_REQUEST_TABLES, raw_path, team_raw_path


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")


def test_nba_inventory_counts_regular_and_playoffs(tmp_path):
    out = tmp_path / "nba_stats"
    tables = list(ALL_TABLES)
    for table in tables[:3]:
        _touch(raw_path(2020, table, "regular", out))
    for table in tables[:2]:
        _touch(raw_path(2020, table, "playoffs", out))
    _touch(team_raw_path(2020, "shot_chart", "BOS", "regular", out))
    n = len(ALL_TABLES) + 30 * len(TEAM_REQUEST_TABLES)

    regular = inventory("nba_stats", 2020, "regular", raw_root=tmp_path)
    assert (regular.have, regular.expected, regular.status) == (4, n, "partial")
    assert inventory("nba_stats", 2020, "playoffs", raw_root=tmp_path).have == 2
    both = inventory("nba_stats", 2020, "both", raw_root=tmp_path)
    assert (both.have, both.expected) == (6, 2 * n)
    assert inventory("nba_stats", 2019, "regular", raw_root=tmp_path).status == "none"


def test_bbref_team_inventory_all(tmp_path):
    for stem in ("team_totals", "opponent_totals", "team_per_100_poss", "opponent_per_100_poss"):
        _touch(tmp_path / f"{stem}_2020.csv")
    assert inventory("bbref_team", 2020, raw_root=tmp_path).status == "all"


def test_bbref_inventory_counts_player_pages(tmp_path):
    _touch(tmp_path / "basketball_reference" / "2020" / "player_totals.html")
    result = inventory("bbref", 2020, raw_root=tmp_path)
    assert (result.have, result.expected) == (1, 8)


def test_darko_inventory_has_no_expected(tmp_path):
    assert inventory("darko", 2020, raw_root=tmp_path).status == "none"
    for day in ("2020-01-01", "2020-01-08"):
        _touch(tmp_path / "darko" / "2020" / f"dpm_{day}.json")
    result = inventory("darko", 2020, raw_root=tmp_path)
    assert (result.have, result.expected, result.status) == (2, None, "partial")
