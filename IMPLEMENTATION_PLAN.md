# Implementation plan for multi-source NBA data architecture

## Phase 1: Warehouse bootstrap

Goal: create a reusable SQLite warehouse and feature-store foundation.

Completed:
- Create `scripts/etl/warehouse.py`
- Create `scripts/etl/feature_store.py`
- Create `scripts/etl/bootstrap.py`
- Validate the database initializes successfully

Remaining:
- Add database connection helpers for reusable imports
- Add schema documentation for each core table

## Phase 2: Source ingestion — done

Goal: ingest both live and historical sources into a raw staging pattern.

Completed:
- Extractors (network only): `scripts/etl/sources/nba_stats/extract.py` (nba_api) and
  `scripts/etl/sources/basketball_reference/extract.py` (league pages + basketball_reference_web_scraper)
- Adapters: `nba_stats`, `bbref_player_season`, `bbref_team_season`, `bbref_web`, `legacy_sample`
- Registry and CLI: `python -m scripts.etl.orchestrator {bootstrap,pull,ingest,features,export,run}`
- `source_manifest` row per file (sha256, counts, status, error); files are skipped when unchanged
- 2025-26 loaded: 582 players, 16 player stat tables, all player and team game logs

## Phase 3: Data normalization and schema mapping — done

Completed:
- Canonical contract, schema and loader in `scripts/etl/canonical/`
- Team ids = NBA abbreviations with source aliases; player ids = Basketball-Reference slugs
- Cross-source player matching by name/team/season, overrides file, review queue (`unresolved_entity`)
- Season from date (end-year convention), Eastern game dates, shared `game_id`
- Source precedence for overlapping rows; per-source long table for player season stats
- Stat catalog (`dim_stat`) documenting every player stat's meaning, unit and direction

## Phase 4: Modeling-ready features

Goal: build operational feature tables for player and team analysis.

Planned outputs:
- `feature_player_daily`
- `feature_team_daily`
- rolling performance features
- efficiency and usage proxies
- recent-form trend features

## Phase 5: Tableau and analysis exports — in progress

Completed: canonical table CSVs, wide per-source stat tables, player game/team season views,
league percentile export (`scripts/etl/export_csvs.py`).


Goal: export clean tables for dashboards and analysis.

Planned outputs:
- CSV exports from `data/clean/`
- Tableau-ready tables in `data/tableau/`
- selected views for player/team trend analysis

## Phase 6: Model pipeline

Goal: train and evaluate predictive models using warehouse tables.

Planned modules:
- `scripts/model/train.py`
- `scripts/model/evaluate.py`

## Validation strategy

- Run `python -m pytest` (offline fixtures, temp databases)
- Run `python -m scripts.etl.bootstrap`
- Validate that database tables exist
- Validate a sample CSV import into the warehouse
- Check schema and model-feature tables are populated
