from __future__ import annotations

import pytest

from pipeline.etl.canonical.dates import eastern_game_date, season_from_date, season_from_label, season_label
from pipeline.etl.canonical.players import normalize_name
from pipeline.etl.canonical.resolver import IdResolver
from pipeline.etl.canonical.stat_catalog import describe
from pipeline.etl.canonical.teams import FRANCHISES, resolve_team_id


def test_thirty_franchises_resolve_by_id_and_name():
    assert len(FRANCHISES) == 30
    for franchise in FRANCHISES:
        assert resolve_team_id(franchise.team_id) == franchise.team_id
        assert resolve_team_id(franchise.team_name.upper()) == franchise.team_id


@pytest.mark.parametrize("raw, expected", [
    ("BRK", "BKN"), ("CHO", "CHA"), ("PHO", "PHX"), ("LA Clippers", "LAC"), ("Seattle SuperSonics", "OKC"),
    ("New Jersey Nets", "BKN"), ("Charlotte Bobcats", "CHA"), ("NEW ORLEANS/OKLAHOMA CITY HORNETS", "NOP"),
    ("Denver Nuggets*", "DEN"), ("League Average", None), ("", None),
])
def test_team_aliases(raw, expected):
    assert resolve_team_id(raw) == expected


@pytest.mark.parametrize("date_id, season", [
    ("2025-10-21", 2026), ("2025-12-31", 2026), ("2026-01-01", 2026), ("2026-06-15", 2026), ("2025-09-30", 2025),
    ("2025-07-31", 2025),
    # 2020 bubble: the 2019-20 season ran to Oct 11, 2020; 2020-21 started Dec 22, 2020.
    ("2020-08-14", 2020), ("2020-10-11", 2020), ("2020-12-22", 2021),
])
def test_season_from_date(date_id, season):
    assert season_from_date(date_id) == season


def test_season_labels_round_trip():
    assert season_label(2026) == "2025-26"
    assert season_from_label("2025-26") == 2026
    assert season_from_label("2000-01") == 2001


@pytest.mark.parametrize("timestamp, expected", [
    ("2000-11-01 00:30:00+00:00", "2000-10-31"),  # 7:30 pm EST the previous evening
    ("2026-03-09 02:30:00+00:00", "2026-03-08"),  # just after DST starts (EDT, -4)
    ("2025-11-02 05:00:00+00:00", "2025-11-02"),  # midnight EST, date-only schedule entry
])
def test_eastern_game_date(timestamp, expected):
    assert eastern_game_date(timestamp) == expected


@pytest.mark.parametrize("raw, expected", [
    ("Nikola Jokić", "nikola jokic"), ("Jaren Jackson Jr.", "jaren jackson"), ("Ronald Holland II", "ronald holland"),
    ("Shaquille O'Neal", "shaquille oneal"), ("Karl-Anthony Towns", "karl anthony towns"),
    ("Ömer Aşık", "omer asik"),
])
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_resolver_matches_by_name_and_disambiguates_by_team_season():
    resolver = IdResolver(
        players=[("jokicni01", "Nikola Jokić"), ("smithja01", "Jalen Smith"), ("smithja02", "Jalen Smith")],
        player_seasons=[("jokicni01", 2026, "DEN"), ("smithja01", 2026, "CHI"), ("smithja02", 2026, "PHX")],
    )
    assert resolver.player("nba_stats", "203999", "Nikola Jokic", "DEN", 2026) == "jokicni01"
    assert resolver.player("nba_stats", "1", "Jalen Smith", "PHX", 2026) == "smithja02"
    assert resolver.player("nba_stats", "2", "Nobody Known", "DEN", 2026, fallback_id="nba_2") == "nba_2"
    assert ("player", "nba_stats", "2") in resolver.unresolved
    assert resolver.xref_player[("nba_stats", "203999")]["match_method"] == "name"


def test_resolver_override_wins():
    resolver = IdResolver(overrides={("nba_stats", "1642380"): "balad01"})
    assert resolver.player("nba_stats", "1642380", "Adama Bal", "MEM", 2026) == "balad01"
    assert not resolver.unresolved


def test_stat_catalog_units_and_direction():
    per_game = describe("basketball_reference", "per_game", "pts_per_g")
    assert (per_game["label"], per_game["unit"], per_game["basis"]) == ("Points per game", "count", "per game")
    assert describe("nba_stats", "per_36", "pts")["label"] == "Points per 36 minutes"
    assert describe("nba_stats", "per_game", "gp")["label"] == "Games played"
    assert describe("nba_stats", "advanced", "def_rating")["higher_is_better"] == 0
    assert describe("basketball_reference", "adj_shooting", "adj_ts_pct")["unit"] == "index"
    assert describe("nba_stats", "shot_zones", "restricted_area_fg_pct")["label"] == "FG%: restricted area"
    assert describe("nba_stats", "usage", "pct_pts")["category"] == "usage"
    assert describe("nba_stats", "totals", "brand_new_stat")["documented"] == 0


def test_stat_catalog_new_nba_tables():
    offense = describe("nba_stats", "play_type_offense", "pr_ball_handler_tov_poss_pct")
    defense = describe("nba_stats", "play_type_defense", "pr_ball_handler_tov_poss_pct")
    assert (offense["higher_is_better"], defense["higher_is_better"]) == (0, 1)
    assert defense["label"] == "P&R ball handler defense turnover rate"
    assert describe("nba_stats", "play_type_defense", "isolation_percentile")["higher_is_better"] == 1
    assert describe("nba_stats", "tracking_drives", "drive_pts_pct")["label"] == "Points per drive"
    assert describe("nba_stats", "defense_3pt", "fg3_pct")["higher_is_better"] == 0  # opponents' 3P%
    assert describe("nba_stats", "tracking_rebounding", "avg_dreb_dist")["unit"] == "feet"
    assert describe("nba_stats", "clutch", "fg_pct")["label"] == "Clutch FG%"
    assert describe("nba_stats", "clutch", "pts")["label"] == "Clutch points"
    assert describe("nba_stats", "hustle", "screen_assists")["category"] == "hustle"


def test_lone_name_match_must_have_played_that_season():
    resolver = IdResolver(players=[("johnsch04", "Chris Johnson")], player_seasons=[("johnsch04", 2026, "HOU")])
    # Another Chris Johnson in 2017, a season whose players are known: not the same person.
    other = IdResolver(players=[("johnsch04", "Chris Johnson"), ("smithjo01", "Joe Smith")],
                       player_seasons=[("johnsch04", 2026, "HOU"), ("smithjo01", 2017, "MIN")])
    assert other.player("nba_stats", "1", "Chris Johnson", "MIN", 2017, fallback_id="nba_1") == "nba_1"
    assert "name_match_not_in_season" in other.unresolved[("player", "nba_stats", "1")]["context"]
    # A season with no canonical players loaded yet still accepts the name match.
    assert resolver.player("nba_stats", "2", "Chris Johnson", "MIN", 2017) == "johnsch04"
