# NBA Player Performance & Decision Intelligence Pipeline

## Project attribution

Created by: Abhinav Nalluri
Portfolio project: NBA player data project
GitHub: @analluri229-cmd

This repository is my personal NBA analytics and decision-intelligence project. It combines public basketball data, custom evaluation metrics, and a reproducible warehouse pipeline for player and team analysis.

The project was built as a hands-on exploration of how raw sports data can be normalized, enriched, and transformed into actionable decision-support views for player evaluation, roster analysis, and performance trends.

## Inspiration and source references

This project draws inspiration from and builds on the work of several public basketball data sources and open-source repositories, including:

- Basketball Reference for historical player, team, and game context
- stats.nba.com for official NBA statistical feeds and game data
- the open-source basketball data ecosystem represented by the repos in this workspace
- the historical NBA Stats Web Data Connector work in [dgrubis.github.io](dgrubis.github.io)
- the extraction and scraping workflows in [basketball_reference_scraper](basketball_reference_scraper) and [basketball_reference_web_scraper](basketball_reference_web_scraper)
- broader reference work in [basketball](basketball), [nba-player-points-prediction](nba-player-points-prediction), and [third_party](third_party)
- the custom metric frameworks documented in [NBA_Player_Evaluation_Metrics.md](NBA_Player_Evaluation_Metrics.md) and [player_evaluation_metrics.md](player_evaluation_metrics.md)

This project is a custom integration and extension of those ideas rather than a standalone system built from scratch. A more detailed attribution and source history is available in [CREDITS.md](CREDITS.md).

## Table of contents
- [Project objective](#project-objective)
- [Workspace structure](#workspace-structure)
- [Multi-source architecture](#multi-source-architecture)
- [Current implementation status](#current-implementation-status)
- [Running the pipeline](#running-the-pipeline)
- [Season coverage and data sourcing](#season-coverage-and-data-sourcing)
- [Recommended next steps](#recommended-next-steps)
- [Notes](#notes)

This workspace is set up to build a Python-based NBA analytics pipeline that blends:

- Basketball Reference data
- Live NBA Stats feeds through the `dgrubis.github.io` WDC integration
- Historical sports data via `octonion/basketball`
- Custom player and team metrics
- Tableau-ready semantic models
- Model-ready feature tables for future ML work

The goal is to help teams understand player performance, identify what is working, and support roster and game decisions through clear, actionable visual analytics.

## Project Objective

We want to combine public basketball statistics with custom business/decision metrics to answer questions like:

- Which players are performing above expectation?
- Which lineup combinations are creating the most value?
- Which players are improving, declining, or underutilized?
- What signals should a team use when deciding on rotation, trade, or contract decisions?

This will ultimately feed Tableau semantic models, a warehouse, and downstream modeling workflows.

## Workspace Structure

- `basketball_reference_scraper/` — installed Python package for Basketball Reference data extraction
- `dgrubis.github.io/` — source repo for the older NBA Stats WDC
- `basketball/` — historical data and scraping repo for backfill/reference work
- `third_party/` — project-level location for external data-source repos
- `data/raw/` — raw source snapshots and extracted files
- `data/clean/` — normalized analysis tables
- `db/sqlite/` — SQLite warehouse and model-ready tables
- `scripts/etl/` — extraction, transformation, load, and feature-store scripts
- `Semantic Models/` — Tableau semantic model work and exported assets
- `.vscode/` — Python workspace settings and debugging config

## Multi-source architecture

Each source has an **extractor**, which downloads raw files and is the only code that touches the network. It also has an **adapter**, which turns one raw file into canonical rows and never touches the database. A single **loader** writes those rows to the warehouse. Features and exports read only canonical tables.

```
extractor (network) --> data/raw/<source>/<season>/...  (unmodified downloads)
adapter   (pure)    --> canonical rows + unresolved names
loader              --> db/sqlite/nba_analytics.db  (one transaction + source_manifest row per file)
features / export   --> feature_player_daily, data/clean/*.csv
```

| Source | Adapter | Raw files | Feeds |
|---|---|---|---|
| stats.nba.com via `nba_api` (primary) | `nba_stats` | `data/raw/nba_stats/<season>/*.json`, plus per-team files in `shot_chart/` and `on_off/` | player season stats (totals, per game, per 36, per 100, advanced, scoring, misc, usage, shot zones, shot distance), tracking (12 tables), closest-defender shooting (defender side), **shooting by closest-defender distance × shot clock** (shooter side, 28 bins), hustle, clutch, Synergy play types (11 offensive, 7 defensive), player bio, player and team game logs, team season stats, lineups, **every field goal attempt** (shot chart), **team stats with each player on and off the court** |
| Basketball-Reference league pages | `bbref_player_season` | `data/raw/basketball_reference/<season>/player_*.html` | player totals, per game, per 36, per 100, advanced, **play-by-play**, shooting, **adjusted shooting** (play-by-play and adjusted shooting exist only here) |
| `fetch_team_stats.py` | `bbref_team_season` | `data/raw/{team,opponent}_{totals,per_100_poss}_<season>.csv` | team/opponent season boxes, ratings, playoff flag |
| `basketball_reference_web_scraper` | `bbref_web` | `data/raw/basketball_reference/<season>/{players_season_totals,standings,season_schedule,player_box_scores_<date>}.csv` | season totals, standings, schedule/results, daily box scores |
| DARKO (www.darko.app) | `darko` | `data/raw/darko/<season>/dpm_<date>.json` | dated player ratings: DPM, offensive/defensive/box/on-off DPM, projected minutes, pace and shooting, salary value |
| Sample files | `legacy_sample` | `data/raw/historical/*.csv`, `data/raw/nba_stats/*.json` | demo player games |

The existing scrapers still work on their own for ad hoc pulls. The pipeline simply ingests whatever they write.

### Canonical ids

- `team_id` is the NBA abbreviation (`GSW`, `BKN`, `PHX`, `CHA`). Basketball-Reference codes (`BRK`, `CHO`, `PHO`) and historical franchise names are aliases. See `scripts/etl/canonical/teams.py`.
- `player_id` is the Basketball-Reference slug (`jokicni01`). Other sources match by normalized name, disambiguated by team and season.
  - Players that can't be matched get a fallback id (`nba_<person id>`) and a row in `unresolved_entity` for review.
  - Fix them in `data/reference/player_xref_overrides.csv`, then run `ingest --force`.
- Seasons are labelled by end year: `2026` = 2025-26. Games from October to December belong to the next year's season.
- `game_id` is `<date>_<away>@<home>` for every source.
- In player season stats, `split = 'TOT'` is the full-season line. Traded players also get one row per team where the source provides it (Basketball-Reference tables, Synergy play types).
  - Synergy lists traded players only per team. The pipeline rebuilds their `TOT` row exactly from the team rows. The Synergy percentile and frequency can't be recombined, so they are left empty.

### Warehouse tables (`scripts/etl/canonical/schema.py`)

| Table | Grain |
|---|---|
| `dim_team`, `dim_player`, `dim_date` | one row per team / player / date |
| `dim_stat` | **data dictionary** for each (source, stat table, stat): label, definition, category, unit, basis, and whether higher is better |
| `fact_player_game`, `fact_team_game` | one row per player-date / team-date |
| `fact_shot` | one row per field goal attempt: location (`loc_x`, `loc_y` in tenths of a foot from the basket), zone, distance, action type, made. `period_seconds_left` is the game clock; the shot clock is only available as season bins in `shot_context` |
| `fact_player_season_stat` | long table: one row per season, season type, player, split, source, stat table and stat |
| `fact_player_rating_daily` | long table: one row per rating date, player, source and stat (DARKO). `date_id` is the last game date the rating includes |
| `fact_player_season`, `fact_team_season`, `fact_team_season_box` | compact season summaries |
| `xref_team`, `xref_player`, `unresolved_entity` | how each source key was mapped; the review queue |
| `source_manifest` | one row per ingested file: sha256, row counts, status, error |
| `feature_player_daily` | rolling features built from `fact_player_game` |

**Merge rules**
- When two sources supply the same game or season row, `nba_stats` > `basketball_reference` > `legacy_sample`. A lower-priority source only fills empty columns.
- `fact_player_season_stat` keeps sources side by side instead of merging them, because sources define some stats differently.
- Every fact row carries the `run_id` of the manifest entry that wrote it.

## Current implementation status

- **Ten seasons are loaded, 2016-17 through 2025-26,** from stats.nba.com and Basketball-Reference.
  - That's 1,478 players with bio data, 38 player stat tables per season (including tracking, hustle, clutch and play types), and every player and team game.
  - The 2025-26 playoffs are included. Earlier seasons are regular season only; add their playoffs with `pull --season-type playoffs`.
- Every NBA player is matched to a Basketball-Reference id: by name, or through `data/reference/player_xref_overrides.csv` for 9 name differences (Cam/Cameron, Cui Cui/Cui Yongxi, ...).
- **Sources agree.** Player-game counts match the raw files in every season. Basketball-Reference season points, NBA season points and summed NBA game logs agree for every player.
- **Seasons come from the source** (2016-17 = 2017). The COVID 2019-20 season, which ran to October 11, 2020 in the bubble, is labelled 2020.
- Event-level play-by-play (`PlayByPlayV3`, about 1,230 requests per season) is deliberately not pulled yet.
- Ingestion is deterministic and idempotent. A file already loaded is skipped by content hash, and `--force` reloads it.
  - A full rebuild of the ten seasons takes about 4 minutes; a no-change run takes about 12 seconds.
- All player stats have catalog entries (`dim_stat`), and exports include league percentiles.
- Offline tests: `python -m pytest`.
- **Sizes (all git-ignored):** raw downloads about 26 MB per season; warehouse about 1.4 GB for ten seasons; latest-season exports about 70 MB.

## Running the pipeline

```
# Download (network). --skip-existing resumes an interrupted pull; failures are listed at the end.
python -m scripts.etl.orchestrator pull --source nba_stats --season 2026 [--season-type regular|playoffs|both]
python -m scripts.etl.orchestrator pull --source nba_stats --season 2017-2025 --skip-existing   # backfill
python -m scripts.etl.orchestrator pull --source bbref --season 2017-2025 --skip-existing       # 8 pages/season
python -m scripts.etl.orchestrator pull --source bbref --with-web-scraper --season 2026         # + totals/schedule/standings
python -m scripts.etl.orchestrator pull --source bbref --date 2025-11-01 --end 2025-11-07       # daily box scores
python fetch_team_stats.py --season 2024 2025 2026 --no-excel                                    # team/opponent tables
python -m scripts.etl.orchestrator pull --source darko --season 2017-2026 [--every 1]          # DARKO, after nba_stats

# Build (offline)
python -m scripts.etl.orchestrator run [--reset]      # bootstrap -> ingest -> features -> export
python -m scripts.etl.orchestrator ingest --source nba_stats --season 2026 [--force]
python -m scripts.etl.orchestrator export [--season 2020 | --all-seasons]
```

Costs per season:
- stats.nba.com: about 140 requests and 6 minutes, doubled with `--season-type both`.
  - About 80 league-wide tables, one request each.
  - `shot_chart` and `on_off` take one request per team (60 per season). The league-wide shot chart stops at 102,400 shots, about half a season.
- DARKO: one request per snapshot, 3 seconds apart. `--season` takes a snapshot every 7 days (`--every N` changes it) on game dates from the season's nba_stats team game log, plus the last regular-season and last playoff dates: about 30 requests per season, or about 190 with `--every 1`.
- Basketball-Reference: 8 pages, rate-limited to 1 request every 4 seconds.
- Missing pages are reported as unavailable and skipped. A Basketball-Reference HTTP 429 (rate limit) stops the pull, because the site then blocks for about an hour.

`bootstrap.cmd` and `demo_pipeline.cmd` still work: `demo_pipeline.cmd` runs the offline `run` step. Only `pull` needs `requests`/`nba_api`; everything else needs just pandas (`requirements.txt`).

Exports cover the **latest season** by default, written to `data/clean/`:
- `--season N` writes that season to `data/clean/season_N/`.
- `--all-seasons` writes every season to `data/clean/`.
- Dimensions, crosswalks, the stat dictionary and the manifest are always complete.
- The long `fact_player_season_stat` table is not exported, because the wide `player_season/` files hold the same values. Query it in `db/sqlite/nba_analytics.db` for multi-season work.

### Reading the stats (exports in `data/clean/`)

- `dim_stat.csv`: what each stat means. Units:
  - `fraction`: 0-1, so 0.456 = 45.6%
  - `percent`: 0-100
  - `index`: 100 = league average
  - `rating`: points per 100 possessions
- `analysis/player_season_percentiles.csv`: every full-season stat with its league percentile among qualified players (500+ regular-season or 100+ playoff minutes). Join to `dim_stat.csv` on `source_system, stat_table, stat_name` for labels and units.
  - `percentile_better` is flipped for stats where lower is better, such as turnovers or defensive rating.
  - It is left empty for stats where direction depends on context, such as usage or shot mix.
- `player_season/<source>_<table>.csv`: one wide table per source and stat table, for notebooks and Tableau.
- `analysis/player_games.csv`, `analysis/team_seasons.csv`: game and season tables with names joined in.
- `player_rating_daily/darko_dpm.csv`: one row per DARKO snapshot date and player.
  - To use it as a model feature without leaking the result, join a game on date G to the player's latest `date_id` **before** G.
  - DARKO data belongs to its authors. Keep it out of anything published, such as Tableau Public.

### Adding a new source adapter

1. Write an extractor that saves unmodified responses under `data/raw/<source>/<season>/`.
2. Write an adapter class with `source_name`, `source_system`, `discover(raw_root)` and `parse(raw, resolver)`. Return rows keyed by canonical table (see `scripts/etl/canonical/contract.py`). Resolve teams and players through `resolver`.
3. Register it in `scripts/etl/sources/registry.py`. If it competes with existing sources, add its `source_system` to `SOURCE_PRECEDENCE`.
4. Add a trimmed real file to `scripts/tests/fixtures/raw/` and a parse test.

## Season coverage and data sourcing

- **Current and recent seasons:** stats.nba.com (`nba_api`) is the primary source, with Basketball-Reference league pages for play-by-play and adjusted shooting. Both cost one request per table per season.
- **Prior seasons:** run the same `pull` commands with other `--season` values. Basketball-Reference covers the full history. stats.nba.com player tables start in 1996-97.
- Raw files are kept per source and season, so any season can be re-ingested or re-normalized later.

## Recommended next steps

1. Backfill prior seasons (`pull` for each season, then `run`) to build the multi-season dataset.
2. Build an interpretation layer on top of `dim_stat` and the percentile export: player profile pages or dashboards, and comparisons against position peers.
3. Add an adapter for the headerless `basketball/bbref/csv` game logs (1983-2015).
4. Merge `team_box_scores` into `fact_team_game`; add Parquet export.
5. Model training on `feature_player_daily` (`scripts/model/`).

## Notes

This project should remain modular and reproducible:

- keep raw extraction code separate from metric logic
- version datasets and transformation logic
- document assumptions for each custom metric
- keep Tableau-ready outputs structured and consistent
- make the project repo the source of truth for all schema and curated data

## Working Goal

The eventual output should be a repeatable NBA analytics workflow that combines:

- trusted external basketball metrics
- proprietary team-context metrics
- a versioned warehouse for historical and live data
- Tableau-friendly semantic data model(s)
- clear visual storytelling for coaching and team decision-makers

## License

The code is released under the [MIT License](LICENSE). It does not cover third-party data: NBA, Basketball-Reference and DARKO data belong to their owners (see [CREDITS.md](CREDITS.md)).
