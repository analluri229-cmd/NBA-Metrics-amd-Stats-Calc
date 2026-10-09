"""Pipeline entry point.

    python -m pipeline.etl.orchestrator bootstrap [--reset]
    python -m pipeline.etl.orchestrator pull --source nba_stats --season 2026 [--season-type playoffs|both]
    python -m pipeline.etl.orchestrator pull --source nba_stats --season 2017-2025 --skip-existing   # backfill
    python -m pipeline.etl.orchestrator pull --source bbref --season 2026 [--tables ...] [--with-web-scraper]
    python -m pipeline.etl.orchestrator pull --source bbref --date 2025-11-01 [--end 2025-11-07]
    python -m pipeline.etl.orchestrator pull --source darko --season 2017-2026 [--every 1]   # after nba_stats
    python -m pipeline.etl.orchestrator pull --source darko --date 2026-01-15 [--end 2026-01-31]
    python -m pipeline.etl.orchestrator ingest [--source NAME ...] [--season N] [--force]
    python -m pipeline.etl.orchestrator features
    python -m pipeline.etl.orchestrator export [--season N | --all-seasons]   # default: latest season
    python -m pipeline.etl.orchestrator run [--reset]        # bootstrap -> ingest -> features -> export

``pull`` is the only step that touches the network; everything else works offline
from the raw files in data/raw/.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from pipeline.etl.bootstrap import bootstrap
from pipeline.etl.canonical.loader import refresh_dim_date_seasons
from pipeline.etl.canonical.stat_catalog import refresh_stat_catalog
from pipeline.etl.export_csvs import export_tables
from pipeline.etl.generate_features import generate_features
from pipeline.etl.paths import CLEAN_DIR, DB_PATH, PROJECT_ROOT, RAW_DIR  # noqa: F401
from pipeline.etl.sources.pulling import PullReport
from pipeline.etl.sources.registry import ADAPTERS, SOURCE_GROUPS, ingest, rows_by_source
from pipeline.etl.warehouse import ensure_schema

HISTORICAL_SOURCES = ("bbref_team_season", "bbref_player_season", "bbref_web")


def run_ingest(db_path: Path | str = DB_PATH, sources: list[str] | None = None, season: int | None = None,
               force: bool = False, raw_root: Path = RAW_DIR) -> list[dict]:
    conn = ensure_schema(db_path)
    try:
        summaries = ingest(conn, sources, season, force, raw_root)
        refresh_stat_catalog(conn)
        refresh_dim_date_seasons(conn)
        return summaries
    finally:
        conn.close()


def run_pipeline(db_path: Path | str = DB_PATH, raw_root: Path = RAW_DIR, export_dir: Path | str | None = None,
                 reset: bool = False, force: bool = False) -> dict[str, object]:
    bootstrap_result = bootstrap(db_path, reset=reset)
    summaries = run_ingest(db_path, force=force, raw_root=raw_root)
    features = generate_features(db_path)
    exports = export_tables(db_path, export_dir or CLEAN_DIR)
    rows = rows_by_source(summaries)
    return {
        "warehouse": bootstrap_result["warehouse"],
        "feature_store": bootstrap_result["feature_store"],
        "historical_rows": sum(rows.get(name, 0) for name in HISTORICAL_SOURCES),
        "live_rows": rows.get("nba_stats", 0),
        "sample_rows": rows.get("legacy_sample", 0),
        "files": _file_status_counts(summaries),
        "failed": [s for s in summaries if s["status"] == "failed"],
        "features": features,
        "exports": len(exports),
    }


def _file_status_counts(summaries: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for summary in summaries:
        counts[summary["status"]] = counts.get(summary["status"], 0) + 1
    return counts


def _print_summaries(summaries: list[dict]) -> None:
    for s in summaries:
        detail = (f"+{s.get('rows_inserted', 0)} ~{s.get('rows_updated', 0)} skipped={s.get('rows_skipped', 0)} "
                  f"unresolved={s.get('rows_unresolved', 0)}") if s["status"] == "success" else s.get("error", "")
        print(f"{s['status']:8s} {s['source_name']:20s} {str(s['season'] or ''):5s} {s['data_type']:28s} {detail}")
    print(f"files: {_file_status_counts(summaries)}")


def parse_seasons(values: list[str]) -> list[int]:
    """['2017-2019', '2026'] -> [2017, 2018, 2019, 2026]."""
    seasons: list[int] = []
    for value in values:
        start, _, end = str(value).partition("-")
        seasons.extend(range(int(start), int(end or start) + 1))
    return sorted(set(seasons))


def _pull(args: argparse.Namespace) -> PullReport:
    report = PullReport()
    seasons = parse_seasons(args.season)
    if args.source == "nba_stats":
        from pipeline.etl.sources.nba_stats.extract import pull_season

        season_type = "both" if args.playoffs else args.season_type
        season_types = ["regular", "playoffs"] if season_type == "both" else [season_type]
        for season in seasons:
            print(f"stats.nba.com {season}:")
            report.merge(pull_season(season, tables=args.tables, season_types=season_types,
                                     skip_existing=args.skip_existing))
    elif args.source in ("bbref", "basketball_reference"):
        from pipeline.etl.sources.basketball_reference import extract

        if args.date:
            extract.pull_box_scores(date.fromisoformat(args.date), date.fromisoformat(args.end or args.date))
        for season in seasons:
            print(f"Basketball-Reference {season}:")
            report.merge(extract.pull_player_tables(season, tables=args.tables, skip_existing=args.skip_existing))
            if args.with_web_scraper:
                extract.pull_season(season)
    elif args.source == "darko":
        from pipeline.etl.sources.darko import extract

        if args.date:
            start, end = date.fromisoformat(args.date), date.fromisoformat(args.end or args.date)
            step = args.every or 1
            days = [date.fromordinal(d).isoformat() for d in range(start.toordinal(), end.toordinal() + 1, step)]
            print(f"DARKO {days[0]} to {days[-1]}:")
            report.merge(extract.pull_dates(days, skip_existing=args.skip_existing))
        for season in seasons:
            print(f"DARKO {season}:")
            report.merge(extract.pull_season(season, every_days=args.every or 7, skip_existing=args.skip_existing))
    else:
        raise SystemExit(f"pull supports --source nba_stats, bbref or darko, not {args.source!r}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Warehouse path. Default: %(default)s")
    commands = parser.add_subparsers(dest="command", required=True)

    boot = commands.add_parser("bootstrap", help="Create the warehouse schema and seed teams.")
    boot.add_argument("--reset", action="store_true", help="Delete the existing warehouse first.")

    pull = commands.add_parser("pull", help="Download raw source files (network).")
    pull.add_argument("--source", required=True, choices=["nba_stats", "bbref", "basketball_reference", "darko"])
    pull.add_argument("--season", nargs="*", default=[],
                      help="Season end year(s) or ranges: 2026 = 2025-26, 2017-2025 = nine seasons.")
    pull.add_argument("--tables", nargs="*", help="Only these tables (default: all for the source).")
    pull.add_argument("--season-type", choices=["regular", "playoffs", "both"], default="regular",
                      help="nba_stats: which season type to pull. Default: %(default)s")
    pull.add_argument("--playoffs", action="store_true", help="nba_stats: same as --season-type both.")
    pull.add_argument("--skip-existing", action="store_true",
                      help="Do not re-download files already in data/raw (resume an interrupted backfill).")
    pull.add_argument("--with-web-scraper", action="store_true",
                      help="bbref: also pull season totals, schedule and standings via basketball_reference_web_scraper.")
    pull.add_argument("--date", help="bbref: pull daily player box scores starting on this date (YYYY-MM-DD). "
                                     "darko: pull the ratings snapshot for this date.")
    pull.add_argument("--end", help="bbref, darko: last date for --date (inclusive).")
    pull.add_argument("--every", type=int,
                      help="darko: days between snapshots. Default: 7 for --season (game dates only), 1 for --date.")

    ing = commands.add_parser("ingest", help="Normalize raw files into the warehouse (offline).")
    ing.add_argument("--source", nargs="*", choices=[*ADAPTERS, *SOURCE_GROUPS])
    ing.add_argument("--season", type=int)
    ing.add_argument("--force", action="store_true", help="Reload files already ingested.")

    commands.add_parser("features", help="Rebuild feature_player_daily.")
    exp = commands.add_parser("export", help="Export warehouse tables to CSV.")
    exp.add_argument("--season", type=int, help="Export this season to data/clean/season_<N>/ (default: latest).")
    exp.add_argument("--all-seasons", action="store_true", help="Export every season to data/clean/.")

    run = commands.add_parser("run", help="bootstrap -> ingest -> features -> export (offline).")
    run.add_argument("--reset", action="store_true")
    run.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "bootstrap":
        print(bootstrap(args.db, reset=args.reset))
    elif args.command == "pull":
        report = _pull(args)
        print(f"pull: {report.summary()}")
        for what, error in report.failed:
            print(f"FAILED {what}: {error}")
        return 1 if report.failed else 0
    elif args.command == "ingest":
        summaries = run_ingest(args.db, args.source, args.season, args.force, raw_root=RAW_DIR)
        _print_summaries(summaries)
        return 1 if any(s["status"] == "failed" for s in summaries) else 0
    elif args.command == "features":
        print({"features_inserted": generate_features(args.db)})
    elif args.command == "export":
        exports = export_tables(args.db, season=args.season, all_seasons=args.all_seasons)
        print(f"exported {len(exports)} files")
    elif args.command == "run":
        result = run_pipeline(args.db, reset=args.reset, force=args.force)
        print(json.dumps({k: v for k, v in result.items() if k != "failed"}, indent=2))
        for failure in result["failed"]:
            print(f"FAILED {failure['file']}: {failure['error']}")
        return 1 if result["failed"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
