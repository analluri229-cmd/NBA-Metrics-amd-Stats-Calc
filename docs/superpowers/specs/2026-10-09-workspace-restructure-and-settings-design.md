# Workspace restructure and pipeline settings: design

Date: 2026-10-09
Status: approved in conversation, awaiting written-spec review
Branch: `chore/restructure` (from `main`)

## Goal

1. **Navigation.** Opening the repo shows four working folders (`pipeline/`, `data/`, `docs/` and `vendor/`) instead of about 30 entries, and it is obvious where our own code lives.
2. **Customizability.** Every value a person might want to change is in one commented file. Running the pipeline with no arguments opens a menu that asks for anything that varies from run to run, such as seasons.

## Non-goals

- No change to what the pipeline downloads, how it normalizes data, or the warehouse schema.
- No cloud warehouse. A hosted copy (MotherDuck was the best free fit) is future work after the project is done.
- No `decision_score`. Its weights were placeholders. Real weights come from the residual-model regressions later.

## Delivery

Two PRs, merged in order, both before any residual-model code is written.

| PR | Branch | Content | Behavior change |
|---|---|---|---|
| 1 | `chore/restructure` | Folder moves and path updates only | None |
| 2 | `feature/pipeline-settings` (from `main` after PR 1) | Settings file, menu, prompts, `bbref_team` source, optional export, source template and guide, `2025-26` season fix, dead-code removal, playoffs default | Yes |

After both merge:
1. Rebase `feature/residual-model` onto `main`.
2. Replace `scripts/` with `pipeline/` in its spec and plan.
3. Add the cross-reference between `pipeline/model/config.py` and `pipeline/settings.py` (see Phase 2, settings).
4. Run the one-time playoff backfill.

---

## Phase 1: folder restructure (PR 1)

### Target layout

```
pipeline/                     was scripts/  (package name changes: scripts.etl -> pipeline.etl)
  etl/                        contents unchanged
  tests/                      contents unchanged, including fixtures/
  fetch_team_stats.py         was at root   (python -m pipeline.fetch_team_stats)
  start_nba_sources.py        was at root   (python -m pipeline.start_nba_sources)
data/
  raw/ clean/ reference/ tableau/          unchanged
  warehouse/nba_analytics.db              was db/sqlite/nba_analytics.db (git-ignored; moved on disk)
docs/
  metrics/NBA_Player_Evaluation_Metrics.md
  metrics/player_evaluation_metrics.md
  guides/workspace_guide.html
  superpowers/                             unchanged
vendor/
  basketball/  basketball_reference_scraper/  basketball_reference_web_scraper/
  nba-player-points-prediction/  dgrubis.github.io/      the 5 submodules, moved with git mv
  nba_api/  flexviz/                                      was third_party/ (git-ignored clones)
local_analysis/                            unchanged (git-ignored, private)

Root files: README.md  LICENSE  CREDITS.md  requirements.txt  pytest.ini
            bootstrap.cmd  demo_pipeline.cmd   (replaced by nba.cmd in PR 2)
```

### Removed in PR 1

- `Semantic Models/` (empty).
- `db/` (empty once the warehouse moves).
- `third_party/` (empty once the clones move).
- `.github/prompts/plan-beginnerFriendlyPythonSetup.prompt.md`, a one-off prompt, and with it `.github/`.
- `IMPLEMENTATION_PLAN.md`, superseded by the README's "Current implementation status".
- `nba_analytics_pipeline/`, the original 222-line scaffold. Nothing imports it, and `scripts/etl` replaced it. Git history keeps it.

`recent 9-29 claude summary.txt` (git-ignored, personal) moves to `local_analysis/chat_exports/`, and its `.gitignore` line is dropped.

### Path updates

Code:
- `pipeline/etl/paths.py`
  - `DB_PATH` becomes `data/warehouse/nba_analytics.db`.
  - `PROJECT_ROOT = parents[2]` stays correct.
- Every `scripts.etl` and `scripts/` import or reference becomes `pipeline.etl` and `pipeline/`. That's about 90 references in 25 files, including `pipeline/tests/`.
- `pipeline/fetch_team_stats.py`: `WORKSPACE_ROOT` becomes `parents[1]`.
- `pipeline/start_nba_sources.py`: `ROOT` becomes `parents[1]`, and `WDC_DIR` becomes `vendor/dgrubis.github.io`.

Config and launchers:
- `pytest.ini`: `testpaths = pipeline/tests`.
- `.vscode/settings.json`: `pytestArgs` becomes `pipeline/tests`.
- `bootstrap.cmd` and `demo_pipeline.cmd`: module paths become `pipeline.etl.*`.
- `.gitignore`:
  - `db/sqlite/*.db` becomes `data/warehouse/*.db`.
  - `third_party/...` becomes `vendor/nba_api/` and `vendor/flexviz/`.
- `.gitmodules` is updated by `git mv`.
- `requirements.txt`: the install comment becomes `pip install -e vendor/basketball_reference_web_scraper -e vendor/basketball_reference_scraper`.

Docs and skills:
- `README.md`, `CREDITS.md`, `docs/guides/workspace_guide.html`: commands, paths and the "Workspace Structure" section.
- `.claude/skills/*` (3 skills plus `template.py`): commands and the warehouse path. `template.py` imports the path from `pipeline.etl.paths` instead of hard-coding it.

Local, not committed:
- `local_analysis/` files that hard-code `db/sqlite/nba_analytics.db`: `darko_decomposition.py`, `eda.ipynb`, `player_profile.ipynb` and `player_profile.backup.ipynb`.
- These matter because `sqlite3.connect` on a missing path silently creates an empty database.

Untouched: `docs/superpowers/` specs and plans are historical records. The residual-model spec and plan are updated on their own branch after the rebase.

### Environment steps

1. Close notebook kernels and anything else holding the warehouse open, because Windows will not move an open file.
2. After the move, reinstall the editable scrapers:
   `pip install -e vendor/basketball_reference_web_scraper -e vendor/basketball_reference_scraper`.
   Today `basketball_reference_scraper` is installed editable from the old root path, so its import breaks until this runs.
3. The two submodules with local working-tree noise (`__pycache__/` in `basketball_reference_scraper`, and `node_modules/.bin` symlink type changes in `dgrubis.github.io`) move as they are. Their recorded commits do not change.

### Commits

1. `git mv` only, so file history follows the moves.
2. Path and reference updates.
3. Docs (README structure section and the rest).

### Verification (all must pass before the PR)

1. **Same test results.** Record the `python -m pytest` summary on `main` first. After the move, the same tests pass with the same counts.
2. **Warehouse found and nothing reloads.** `python -m pipeline.etl.orchestrator ingest` reports every file as skipped by content hash.
3. **Submodules intact.** `git submodule status` lists all 5 under `vendor/` at the same commits as before.
4. **Scrapers import.** `python -c "import basketball_reference_scraper, basketball_reference_web_scraper"` succeeds after the reinstall.
5. **No stale references.** `git grep -nE "scripts[./]|db/sqlite|third_party"` returns nothing outside `docs/superpowers/`.
6. **Launchers work.** `demo_pipeline.cmd` completes.
7. **Notebooks run.** `player_profile.ipynb` runs against the new warehouse path, via `local_analysis/run_profile.py`.

### Rollback

`git revert` the PR, then move `data/warehouse/nba_analytics.db` back to `db/sqlite/` and reinstall the scrapers from the old paths. The PR description includes these commands.

---

## Phase 2: settings, menu and cleanup (PR 2)

### `pipeline/settings.py`

This is the one file for values a person may change. Every entry has a comment covering what it does, the allowed values, and the cost or risk of changing it.

| Group | Setting | Default | Notes in the comment |
|---|---|---|---|
| Seasons | `CURRENT_SEASON` | `None` | `None` means the season containing today, switching over on **Nov 1**, which is after every normal tip-off. Set an end year to pin it. Labelled by end year: 2026 = 2025-26 |
| | `SEASONS` | `range(2017, 2027)` | used as the backfill default |
| | `SEASON_TYPE` | `"both"` | `"regular"`, `"playoffs"` or `"both"`. `"both"` doubles stats.nba.com requests (about 6 to 12 min per season) |
| Sources | `DEFAULT_SOURCES` | `("nba_stats", "bbref", "bbref_team")` | DARKO is left out on purpose because its data is personal-use only |
| | `BBREF_WITH_WEB_SCRAPER` | `False` | adds totals, schedule and standings |
| | `DARKO_EVERY_DAYS` | `7` | days between snapshots. `1` means about 190 requests per season |
| | `NBA_STATS_TABLES` | `()` | empty means all tables. Otherwise a subset of the names in `nba_stats/extract.py` |
| Request pacing | `NBA_STATS_DELAY_SECONDS` | `1.5` | |
| | `BBREF_DELAY_SECONDS` | `4` | **below about 3 s, Basketball-Reference blocks you for about an hour (HTTP 429)** |
| | `DARKO_DELAY_SECONDS` | `3` | |
| Team tables | `TEAM_STATS_EXCEL` | `True` | also writes the Tableau workbook to `data/tableau/` |
| Exports | `EXPORT_AFTER_RUN` | `False` | `run` no longer exports unless this is set or the menu answer is yes |
| | `QUALIFY_MINUTES` | `{"regular": 500, "playoffs": 100}` | minutes a player needs to count in league percentiles |
| Folders | `DATA_DIR`, `RAW_DIR`, `CLEAN_DIR`, `TABLEAU_DIR`, `WAREHOUSE_PATH` | as in Phase 1 | |

Rules:
- `paths.py` stays, because about 10 modules import it. It reads its base folders from `settings.py`.
- Extractors, the exporter and the `bbref_team` source read their values from `settings.py`, and the hard-coded copies are deleted. Function parameters such as `delay=` keep their defaults, but those defaults now come from settings, so tests can still pass explicit values.
- **Fixed definitions stay in their modules**, each with a one-line comment saying they are not settings. Examples are the stats.nba.com endpoint names, the play-type and tracking-measure lists, and the closest-defender and shot-clock bins.
- **Precedence:** a command-line option wins, then the menu answer, then `settings.py`.
- **Validation:** `settings.validate()` runs at startup of the orchestrator and the menu. A bad value raises an error that names the setting and says what's allowed. Examples:
  - a season below 1997 for stats.nba.com
  - an unknown `SEASON_TYPE`
  - `BBREF_DELAY_SECONDS < 3`
  - a non-positive `QUALIFY_MINUTES`
- **The model keeps its own config.** The residual model's `pipeline/model/config.py` holds model settings. Each file's header comment points to the other ("pipeline settings live in `pipeline/settings.py`" and "model settings live in `pipeline/model/config.py`").

### `bbref_team` pull source

- `fetch_team_stats.py`'s download logic moves into `pipeline/etl/sources/basketball_reference/team_extract.py` and is registered as `pull --source bbref_team`.
- It writes the same files to the same place (`data/raw/{team,opponent}_{totals,per_100_poss}_<season>.csv`), so the existing `bbref_team_season` adapter and the warehouse are unchanged.
- It writes the Excel workbook when `TEAM_STATS_EXCEL` is set.
- `pipeline/fetch_team_stats.py` is deleted, and the README and the `pulling-nba-data` skill switch to the new command.

### Season parsing fix

`parse_seasons` today turns `2025-26` into `range(2025, 27)`, which is empty, so a pull downloads nothing without any error. The fix:
- `YYYY-YY` (two-digit second part) is a season label: `2025-26` → `[2026]`.
- `YYYY-YYYY` (four-digit second part) is always a range of end years, exactly as today: `2017-2025` → nine seasons, and `2025-2026` → `[2025, 2026]`.
- A descending range such as `2025-2017` raises `ValueError` with a message.
- The same parser serves the command line and the menu.

### `pipeline/prompts.py`

These are reusable prompts in the style of `local_analysis/find_player.py`:
- `ask_seasons(default)`: re-asks until the answer is valid, Enter accepts the default, and it echoes the parsed range.
- `ask_yes_no(question, default)`: re-asks until the answer is y or n.
- `ask_choice(question, options, default)`: used for season type and the menu itself.

All three read through an `input` parameter that defaults to the built-in, so tests can script the answers.

### Download check

`pipeline/etl/sources/inventory.py` reports, per source, season and season type, what is already on disk:

| Source | Reported as |
|---|---|
| `nba_stats` | league tables `have/expected`, from `ALL_TABLES`, plus per-team tables `have/expected` (30 teams × team tables) |
| `bbref` | player pages `have/8` |
| `bbref_team` | CSVs `have/4` |
| `darko` | number of snapshots on disk (no fixed expected count) |

How the menu uses each result, for each season it is about to pull:

| On disk | Message | Yes means | Default |
|---|---|---|---|
| Nothing | "<season>: no data yet. Download it? (about N minutes)" | full pull | Yes |
| Some | "<season>: X of Y files already downloaded. Download the missing Z?" | pull with `--skip-existing` | Yes |
| All | "<season>: all Y files already downloaded. Download again? This replaces the saved files" | full pull | **No** |

The "about N minutes" estimate is the number of requests still needed × the source's delay setting, rounded up to whole minutes.

### Menu: `python -m pipeline` (`pipeline/__main__.py`)

```
1) Update current season   pull DEFAULT_SOURCES for CURRENT_SEASON (SEASON_TYPE), then build
2) Backfill seasons        asks: seasons, sources, season type
3) Daily box scores        asks: start date, end date
4) DARKO ratings           asks: seasons (warns: personal use only)
5) Rebuild warehouse       offline: ingest -> features
6) Export CSVs             asks: latest / one season / all seasons
q) Quit
```

- Every question offers the `settings.py` value as its default.
- Options 1 to 4 run the download check before pulling, then ask "Load the new files into the warehouse now?", then "Export CSVs too?" (default from `EXPORT_AFTER_RUN`).
- **Single code path.** The menu only builds lists of command-line options and calls `orchestrator.main(argv)`. Before each call it prints the equivalent command (`-> python -m pipeline.etl.orchestrator pull --source nba_stats --season 2026 --season-type both`).
- **When there is no terminal** (stdin not a TTY, as with Claude, scripts or CI), it prints the orchestrator help and exits 0 instead of blocking.
- `nba.cmd` at the root runs `py -3 -m pipeline` so it can be double-clicked. It replaces `bootstrap.cmd` and `demo_pipeline.cmd`, which are deleted.

### Optional export

- `run` builds without exporting (ingest → features). It exports only when `EXPORT_AFTER_RUN` is true or `run --export` is passed.
- The `export` command is unchanged.
- The README and skills are updated to say `run --export` where they relied on `run` exporting.

### Source template and guide

- `pipeline/etl/sources/_template/` contains `extract.py` and `adapter.py`. They are a copyable skeleton with `# FILL IN:` comments at each decision point: the URL and request, the raw file naming, `discover()`, `parse()` row mapping, and resolver calls. It is not registered.
- `docs/guides/adding-a-source.md` walks through the four steps (extractor, adapter, registry line with optional `SOURCE_PRECEDENCE`, fixture and test) using the template, and lists the `settings.py` entries a new source should add (delay, defaults).

### Dead-code removal

| File | Evidence | Action |
|---|---|---|
| `pipeline/etl/live_ingest.py` | imported by nothing | delete |
| `pipeline/etl/historical_ingest.py` | imported by nothing | delete |
| `pipeline/etl/sample_backfill.py` | imported by nothing | delete |
| `pipeline/etl/normalize.py` | imported by nothing (`normalize_name` comes from `canonical/players.py`) | delete |
| `pipeline/etl/run_demo_pipeline.py` | only `demo_pipeline.cmd` used it, and that is replaced by `nba.cmd` | delete |
| `canonical_mapping.py`, `bootstrap.py`, `generate_features.py`, `feature_store.py` | imported by the orchestrator or bootstrap | **keep** |

Each deletion is confirmed by `git grep` and a full test run in the same commit.

### Tests (all offline, written before the code)

| Area | Test |
|---|---|
| settings | changing a setting changes the delay or threshold the extractor or exporter uses; `validate()` rejects each bad value with a message naming the setting |
| `CURRENT_SEASON` | `None` gives 2026 for 2026-10-31 and 2027 for 2026-11-01; a pinned value wins |
| `parse_seasons` | `2026` → [2026]; `2025-26` → [2026]; `2025-2026` → [2025, 2026]; `2017-2025` → 9 seasons; `2025-2017` → error; `2010-2012 2026` → 4 seasons |
| prompts | scripted answers: bad then good, Enter takes the default, and y/n re-asks |
| inventory | a temporary raw folder with some regular and some playoff files gives the right have/expected per season type |
| menu | scripted answers produce the expected argv lists (with `orchestrator.main` mocked); with no TTY it prints help and exits 0 |
| `bbref_team` | given a saved season page fixture, it writes the same four CSVs that `fetch_team_stats.py` produced, and the adapter output is unchanged |
| export | `run` without `--export` writes nothing to `data/clean/`, and `run --export` writes the usual files |
| template | `_template` modules import, and the adapter class has `source_name`, `source_system`, `discover` and `parse` |
| regression | the full existing suite passes |

### After PR 2: playoff backfill

Menu → **2) Backfill seasons** → `2017-2025` → `playoffs`. This adds playoff tables for 2016-17 through 2024-25: about 9 × 6 minutes on stats.nba.com, and existing files are skipped. Then rebuild. Basketball-Reference playoff tables already load from the existing pages. DARKO's last-playoff-date snapshots need the nba_stats playoff game logs first, so pull DARKO afterwards if it's wanted.

---

## Future work (not in this spec)

- **Cloud warehouse mirror.** MotherDuck's free plan (10 GB) fits the warehouse, and DuckDB reads SQLite directly. It would be a read-only mirror uploaded after builds, with an option to leave DARKO out. Revisit after the project is done, and check current free limits then.
- **`decision_score`.** Derive weights from the residual-model regressions instead of hand-picking them.
