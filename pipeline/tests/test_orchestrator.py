from __future__ import annotations

import csv

from pipeline.etl.orchestrator import main, run_pipeline


def test_run_pipeline_returns_summary(tmp_path, raw_root) -> None:
    result = run_pipeline(tmp_path / "warehouse.db", raw_root=raw_root, export_dir=tmp_path / "clean")

    assert isinstance(result, dict)
    assert "warehouse" in result
    assert "feature_store" in result
    assert "sample_rows" in result
    assert result["failed"] == []
    assert result["historical_rows"] > 0 and result["live_rows"] > 0


def test_run_pipeline_exports_notebook_files(tmp_path, raw_root) -> None:
    clean = tmp_path / "clean"
    run_pipeline(tmp_path / "warehouse.db", raw_root=raw_root, export_dir=clean)

    for name in ("dim_stat.csv", "fact_player_game.csv", "analysis/player_games.csv",
                 "analysis/team_seasons.csv", "analysis/player_season_percentiles.csv",
                 "player_season/nba_stats_totals.csv", "player_season/basketball_reference_advanced.csv"):
        assert (clean / name).exists(), name

    with (clean / "dim_stat.csv").open(encoding="utf-8") as handle:
        catalog = list(csv.DictReader(handle))
    assert catalog and all(row["documented"] == "1" for row in catalog)

    with (clean / "player_season" / "basketball_reference_totals.csv").open(encoding="utf-8") as handle:
        wide = list(csv.DictReader(handle))
    jokic = next(r for r in wide if r["player_id"] == "jokicni01" and r["season_type"] == "regular")
    assert jokic["split"] == "TOT" and float(jokic["pts"]) > 1000


def test_cli_ingest_reports_success(tmp_path, raw_root, monkeypatch, capsys) -> None:
    monkeypatch.setattr("pipeline.etl.orchestrator.RAW_DIR", raw_root)
    db = tmp_path / "cli.db"
    assert main(["--db", str(db), "bootstrap"]) == 0
    assert main(["--db", str(db), "ingest", "--source", "bbref"]) == 0
    assert "success" in capsys.readouterr().out


def test_export_defaults_to_latest_season(tmp_path, raw_root) -> None:
    from pipeline.etl.export_csvs import export_tables

    db = tmp_path / "warehouse.db"
    run_pipeline(db, raw_root=raw_root, export_dir=tmp_path / "clean")
    assert not (tmp_path / "clean" / "fact_player_season_stat.csv").exists()  # warehouse only

    latest = tmp_path / "latest"
    export_tables(db, latest)
    with (latest / "fact_player_season.csv").open(encoding="utf-8") as handle:
        assert {row["season"] for row in csv.DictReader(handle)} == {"2026"}

    everything = tmp_path / "all"
    export_tables(db, everything, all_seasons=True)
    with (everything / "fact_player_season.csv").open(encoding="utf-8") as handle:
        assert {row["season"] for row in csv.DictReader(handle)} == {"2001", "2026"}
    with (everything / "dim_player.csv").open(encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) > 4  # dimensions are never season-filtered


def test_team_and_lineup_exports(tmp_path, raw_root) -> None:
    clean = tmp_path / "clean"
    run_pipeline(tmp_path / "warehouse.db", raw_root=raw_root, export_dir=clean)
    for name in ("team_season/nba_stats_hustle.csv", "team_season/nba_stats_advanced.csv",
                 "lineup_season/nba_stats_5man_advanced.csv", "analysis/team_season_ranks.csv"):
        assert (clean / name).exists(), name
    with (clean / "analysis" / "team_season_ranks.csv").open(encoding="utf-8") as handle:
        ranks = [r for r in csv.DictReader(handle) if r["stat_table"] == "advanced" and r["stat_name"] == "def_rating"]
    best = min(ranks, key=lambda r: float(r["value"]))
    assert best["rank"] == "1"  # lowest defensive rating ranks first
    with (clean / "dim_stat.csv").open(encoding="utf-8") as handle:
        entities = {r["entity"] for r in csv.DictReader(handle)}
    assert entities == {"player", "team", "lineup"}
