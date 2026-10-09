---
name: pulling-nba-data
description: Use when downloading or refreshing NBA data in this workspace - updating the current season, backfilling older seasons, adding playoffs, pulling daily box scores or DARKO ratings, or when new data doesn't show up in the warehouse or data/clean/ after a download.
---

# Pulling NBA Data

## The three steps

Downloading alone changes nothing you can query. Every pull is followed by ingest (and export, for CSVs):

```
pull    (network)  -> data/raw/<source>/<season>/     unmodified downloads
ingest  (offline)  -> data/warehouse/nba_analytics.db      normalized warehouse
export  (offline)  -> data/clean/*.csv                latest season by default
```

`python -m pipeline.etl.orchestrator run` does bootstrap (creates tables if missing) -> ingest (every source, every season) -> features. Add `--export` to also write `data/clean/` (latest season), or set `EXPORT_AFTER_RUN = True` in `pipeline/settings.py`. `run --force` reloads every file.
For a person at a console, `python -m pipeline` (or `nba.cmd`) is a guided menu over the same commands; it checks what is already downloaded. Run non-interactively (as Claude does) it just prints the CLI help, so use the commands below.
Defaults (seasons, `SEASON_TYPE = "both"`, default sources, delays) live in `pipeline/settings.py`.
Run everything from the project root with the project's venv active.

Which seasons are already loaded:
`python -c "import sqlite3; print(sqlite3.connect('data/warehouse/nba_analytics.db').execute('select distinct season from fact_player_season_stat').fetchall())"`

## Common jobs

| Job | Commands |
|---|---|
| Refresh current season mid-year | `pull --source nba_stats --season 2026`, then `bbref`, `bbref_team` and `darko` for 2026, then `run --export` |
| Add playoffs | `pull --source nba_stats --season 2026 --season-type playoffs`, then `pull --source darko --season 2026 --skip-existing` (adds the last-playoff-date snapshot), then `run` |
| Backfill older seasons | `pull --source nba_stats --season 2017-2025 --skip-existing`, same for `bbref`, then `run` |
| Only some tables | add `--tables advanced shot_zones` |
| Daily box scores (BBRef) | `pull --source bbref --date 2025-11-01 --end 2025-11-07` then `run` |
| Team/opponent tables | `pull --source bbref_team --season 2024-2026` then `run` (also writes `data/tableau/team_stats_<season>.xlsx` unless `TEAM_STATS_EXCEL = False`) |
| Totals, standings, schedule | `pull --source bbref --with-web-scraper --season 2026` then `run` |
| DARKO ratings | `pull --source darko --season 2026` **after** the nba_stats pull for that season (it reads game dates from `data/raw/nba_stats/<season>/team_game_log.json`; no ingest needed in between) |
| CSVs for an older season | `export --season 2020` (writes `data/clean/season_2020/`) or `export --all-seasons` |

All `pull`/`ingest`/`export`/`run` commands are `python -m pipeline.etl.orchestrator <command> ...`. `--season` takes end years: `2026` = 2025-26; season labels like `2025-26` and ranges like `2017-2025` work for `pull`.

## Things that go wrong

- **`--skip-existing` on the current season** skips files already on disk, so nothing refreshes. Use it only to resume an interrupted backfill.
- **Pulled but `data/clean/` is stale**: the pull only wrote `data/raw/`, and `run` doesn't export by default. Run `run --export` (or `export`).
- **Ran `run` and the warehouse still didn't change**: ingest skips files whose content hash was already loaded. Changed raw files load automatically; to reload unchanged ones use `ingest --source nba_stats --season 2026 --force`, then `export`.
- **Basketball-Reference HTTP 429** stops the pull: the site blocks for about an hour. Wait, then rerun with `--skip-existing`.
- **`FAILED ...` lines / exit code 1**: listed at the end of the pull. Rerun the same command with `--skip-existing` to fetch only what's missing.
- **Unresolved players** after ingest: fallback id `nba_<person id>` plus a row in `unresolved_entity`. Add the mapping to `data/reference/player_xref_overrides.csv`, then `ingest --force`.

## Cost

- stats.nba.com: ~140 requests, ~6 minutes per season type per season (1.5 s between requests).
- Basketball-Reference: 8 pages per season, 4 s apart.
- DARKO: ~30 requests per season (weekly snapshots; `--every 1` for daily, ~190).
- `run` over ten seasons: ~4 minutes; ~12 seconds when nothing changed.

## Data you must not publish

DARKO ratings belong to their authors. Local use (warehouse, modeling, Tableau Desktop) is fine; commercial use needs DARKO's permission, and their chart-reuse permission doesn't cover bulk data. Keep `data/raw/darko/`, `data/clean/player_rating_daily/`, and anything built from `fact_player_rating_daily` out of git, Tableau Public, or any shared output. Charts for your own use are fine. Don't write scrapers for sites whose terms forbid them (e.g. EPM / dunksandthrees.com).
