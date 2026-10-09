"""Adapters parse fixture raw files (trimmed real downloads) into canonical rows, without a database."""
from __future__ import annotations

from pipeline.etl.canonical.resolver import IdResolver
from pipeline.etl.sources.basketball_reference.player_season import PlayerSeasonAdapter
from pipeline.etl.sources.basketball_reference.team_season import TeamSeasonAdapter
from pipeline.etl.sources.basketball_reference.web_scraper import WebScraperAdapter
from pipeline.etl.sources.legacy.sample import LegacySampleAdapter
from pipeline.etl.sources.nba_stats.adapter import NbaStatsAdapter


def _parse(adapter, raw_root, data_type, resolver=None):
    raw = next(r for r in adapter.discover(raw_root) if r.data_type == data_type)
    return adapter.parse(raw, resolver or IdResolver())


def test_team_season_per_100_sets_ratings(raw_root):
    team = _parse(TeamSeasonAdapter(), raw_root, "team_per_100_poss").records
    opponent = _parse(TeamSeasonAdapter(), raw_root, "opponent_per_100_poss").records
    den_off = next(r for r in team["fact_team_season"] if r["team_id"] == "DEN")
    den_def = next(r for r in opponent["fact_team_season"] if r["team_id"] == "DEN")
    assert den_off["off_rtg"] == 122.6 and den_off["playoff_appearance"] == 1
    assert den_def["def_rtg"] is not None and "off_rtg" not in den_def
    assert {r["team_id"] for r in team["fact_team_season_box"]} == {"DEN", "BOS", "LAC"}


def test_team_season_discovers_all_four_tables(raw_root):
    types = {r.data_type for r in TeamSeasonAdapter().discover(raw_root)}
    assert types == {"team_totals", "opponent_totals", "team_per_100_poss", "opponent_per_100_poss"}


def test_bbref_player_page_splits_traded_players(raw_root):
    result = _parse(PlayerSeasonAdapter(), raw_root, "totals")
    stats = result.records["fact_player_season_stat"]
    harden = {(r["season_type"], r["split"]) for r in stats if r["player_id"] == "hardeja01"}
    assert ("regular", "TOT") in harden
    assert len({split for season_type, split in harden if season_type == "regular"}) == 3  # TOT + 2 teams
    jokic_pts = next(r for r in stats if r["player_id"] == "jokicni01" and r["stat_name"] == "pts"
                     and r["season_type"] == "regular")
    assert jokic_pts["split"] == "TOT" and jokic_pts["team_id"] == "DEN" and jokic_pts["value"] > 1000
    assert any(r["season_type"] == "playoffs" for r in stats)
    compact = {r["player_season_id"] for r in result.records["fact_player_season"]}
    assert "2026_hardeja01_TOT" in compact and "2026_jokicni01_TOT" in compact


def test_bbref_player_page_keeps_full_precision_values(raw_root):
    stats = _parse(PlayerSeasonAdapter(), raw_root, "advanced").records["fact_player_season_stat"]
    usage = next(r for r in stats if r["player_id"] == "jokicni01" and r["stat_name"] == "usg_pct")
    assert 0 < usage["value"] < 1  # fraction from the csk sort key, not the displayed 30.4


def test_web_scraper_outputs(raw_root):
    adapter = WebScraperAdapter()
    totals = _parse(adapter, raw_root, "players_season_totals").records
    assert next(r for r in totals["fact_player_season"] if r["player_id"] == "stackje01")["ppg"] == 29.8

    boxes = _parse(adapter, raw_root, "player_box_scores").records["fact_player_game"]
    mobley = next(r for r in boxes if r["player_id"] == "moblecu01")
    assert mobley["date_id"] == "2001-01-01" and mobley["season"] == 2001
    assert mobley["points"] == 30 and mobley["home_away"] == "A" and mobley["game_id"] == "2001-01-01_HOU@MIN"

    games = _parse(adapter, raw_root, "season_schedule").records["fact_team_game"]
    assert games[0]["date_id"] == "2000-10-31"  # 00:30 UTC is the previous evening in the East
    assert {g["home_away"] for g in games[:2]} == {"H", "A"}

    standings = _parse(adapter, raw_root, "standings").records["fact_team_season"]
    assert next(r for r in standings if r["team_id"] == "PHI")["wins"] == 56


def test_nba_player_season_uses_full_season_split_and_matches_bbref(raw_root):
    resolver = IdResolver(players=[("jokicni01", "Nikola Jokić"), ("hardeja01", "James Harden")])
    result = _parse(NbaStatsAdapter(), raw_root, "player_season_totals", resolver)
    stats = result.records["fact_player_season_stat"]
    assert {r["split"] for r in stats} == {"TOT"}
    assert not any(r["stat_name"].endswith("_rank") for r in stats)
    assert {r["player_id"] for r in stats} >= {"jokicni01", "hardeja01"}
    assert resolver.xref_player[("nba_stats", "1642380")]["player_id"] == "nba_1642380"  # Adama Bal: no match


def test_nba_shot_zones_flatten_two_level_headers(raw_root):
    stats = _parse(NbaStatsAdapter(), raw_root, "player_season_shot_zones").records["fact_player_season_stat"]
    names = {r["stat_name"] for r in stats}
    assert {"restricted_area_fga", "restricted_area_fg_pct", "mid_range_fgm"} <= names


def test_nba_bio_fills_dim_player(raw_root):
    resolver = IdResolver(players=[("jokicni01", "Nikola Jokić")])
    rows = _parse(NbaStatsAdapter(), raw_root, "player_bio", resolver).records["dim_player"]
    jokic = next(r for r in rows if r["player_id"] == "jokicni01")
    assert (jokic["height"], jokic["weight"], jokic["draft_year"], jokic["draft_number"]) == (83, 284, 2014, 41)
    assert jokic["country"] == "Serbia" and jokic["college"] is None


def test_nba_tracking_hustle_defense_tables(raw_root):
    adapter = NbaStatsAdapter()
    drives = _parse(adapter, raw_root, "player_season_tracking_drives").records["fact_player_season_stat"]
    assert {r["stat_table"] for r in drives} == {"tracking_drives"}
    names = {r["stat_name"] for r in drives}
    assert "drive_pts_pct" in names and not names & {"w", "l", "w_pct"}  # team record is dropped from tracking

    defense = _parse(adapter, raw_root, "player_season_defense_3pt").records["fact_player_season_stat"]
    assert {r["split"] for r in defense} == {"TOT"} and "fg3_pct" in {r["stat_name"] for r in defense}
    assert not {"close_def_person_id", "player_position"} & {r["stat_name"] for r in defense}

    hustle = _parse(adapter, raw_root, "player_season_hustle").records["fact_player_season_stat"]
    assert "deflections" in {r["stat_name"] for r in hustle}


def test_play_types_rebuild_full_season_for_traded_players(raw_root):
    stats = _parse(NbaStatsAdapter(), raw_root, "player_season_play_type_isolation_offense") \
        .records["fact_player_season_stat"]
    assert {r["stat_table"] for r in stats} == {"play_type_offense"}
    harden = {(r["split"], r["stat_name"]): r["value"] for r in stats if r["player_id"] == "nba_201935"}
    team_splits = {split for split, _ in harden} - {"TOT"}
    assert team_splits == {"LAC", "CLE"}
    poss = [harden[(team, "isolation_poss")] for team in team_splits]
    pts = [harden[(team, "isolation_pts")] for team in team_splits]
    assert harden[("TOT", "isolation_poss")] == sum(poss)
    assert harden[("TOT", "isolation_ppp")] == round(sum(pts) / sum(poss), 3)
    assert ("TOT", "isolation_percentile") not in harden  # cannot be recombined across teams
    jokic = {r["split"] for r in stats if r["player_id"] == "nba_203999"}
    assert jokic == {"TOT"}


def test_nba_game_logs(raw_root):
    players = _parse(NbaStatsAdapter(), raw_root, "player_game_log").records["fact_player_game"]
    assert all(r["game_id"] and r["home_away"] in ("H", "A") for r in players)
    teams = _parse(NbaStatsAdapter(), raw_root, "team_game_log").records["fact_team_game"]
    for row in teams:
        assert row["team_id"] == "DEN" and row["off_rtg"] > 0
        assert round(row["off_rtg"] - row["def_rtg"], 1) == row["net_rtg"]


def test_legacy_sample_falls_back_for_unknown_players(raw_root):
    resolver = IdResolver()
    result = _parse(LegacySampleAdapter(), raw_root, "player_game_csv", resolver)
    ids = {r["player_id"] for r in result.records["fact_player_game"]}
    assert ids == {"name_nikola_jokic", "name_mystery_player"}
    assert len(resolver.unresolved) == 2


def test_team_stats_go_to_the_team_long_table(raw_root):
    adapter = NbaStatsAdapter()
    hustle = _parse(adapter, raw_root, "team_season_hustle").records["fact_team_season_stat"]
    assert {r["team_id"] for r in hustle} == {"DEN", "BOS", "LAC"} and {r["stat_table"] for r in hustle} == {"hustle"}
    advanced = _parse(adapter, raw_root, "team_season_advanced").records
    assert "fact_team_season" in advanced  # still feeds the compact team season table
    assert {r["stat_table"] for r in advanced["fact_team_season_stat"]} == {"advanced"}
    iso = _parse(adapter, raw_root, "team_season_play_type_isolation_offense").records["fact_team_season_stat"]
    assert {r["stat_table"] for r in iso} == {"play_type_offense"} and "isolation_ppp" in {r["stat_name"] for r in iso}


def test_lineups_map_members_through_the_crosswalk(raw_root):
    resolver = IdResolver(xref={("nba_stats", "203999"): ("jokicni01", "name")})
    result = _parse(NbaStatsAdapter(), raw_root, "lineups_5man_advanced", resolver)
    lineups = result.records["dim_lineup"]
    assert lineups and all(l["group_size"] == 5 and l["lineup_id"].startswith("DEN:") for l in lineups)
    members = result.records["bridge_lineup_player"]
    assert len(members) == 5 * len(lineups)
    assert any(m["player_id"] == "jokicni01" for m in members)
    stats = {r["stat_name"] for r in result.records["fact_lineup_season_stat"]}
    assert {"net_rating", "min"} <= stats and not {"group_id", "sum_time_played"} & stats


def test_split_defense_season_is_recombined():
    from pipeline.etl.sources.nba_stats.adapter import combine_defense_stints

    # Mikal Bridges 2022-23, listed twice (F and G-F) in the closest-defender table.
    stints = [{"gp": 56, "g": 56, "freq": 1.0, "d_fgm": 349, "d_fga": 730, "d_fg_pct": 0.478, "normal_fg_pct": 0.474},
              {"gp": 26, "g": 26, "freq": 1.0, "d_fgm": 176, "d_fga": 382, "d_fg_pct": 0.461, "normal_fg_pct": 0.476}]
    total = combine_defense_stints("defense_overall", stints)
    assert (total["gp"], total["d_fgm"], total["d_fga"], total["freq"]) == (82, 525, 1112, 1.0)
    assert total["d_fg_pct"] == round(525 / 1112, 3)
    assert total["pct_plusminus"] == round(total["d_fg_pct"] - total["normal_fg_pct"], 3)
