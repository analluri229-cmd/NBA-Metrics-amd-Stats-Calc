# Workspace Restructure and Pipeline Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the repo into `pipeline/`, `data/`, `docs/` and `vendor/` without changing behavior (PR 1). Then give the pipeline one commented settings file, a guided `python -m pipeline` menu, a `bbref_team` pull source, optional export, a source template, the `2025-26` season fix and dead-code removal (PR 2).

**Architecture:**
- PR 1 is `git mv` plus mechanical path rewrites, proven by an unchanged test count and a no-op ingest.
- In PR 2, `pipeline/settings.py` holds every tunable value, and consumers read it at call time.
- The menu (`pipeline/__main__.py`) only builds argv lists for `pipeline.etl.orchestrator.main()`, so the CLI and the menu share one code path.

**Tech Stack:** Python 3.11+ (stdlib `argparse`, `sqlite3`), pandas, pytest, nba_api, requests. Windows 11 with Git Bash and PowerShell.

**Spec:** `docs/superpowers/specs/2026-10-09-workspace-restructure-and-settings-design.md`

## Global Constraints

- PR 1 changes no behavior. `python -m pytest` must report **87 passed** before and after; that is the baseline recorded on `main` (`ce05455`).
- Package name `scripts` becomes `pipeline`. Every command becomes `python -m pipeline.etl.orchestrator ...`.
- Warehouse path: `data/warehouse/nba_analytics.db` (git-ignored).
- `docs/superpowers/` is history: never rewrite paths inside it, except in the residual-model spec and plan during Task 14.
- Nothing under `local_analysis/` is ever committed. DARKO data is never committed. Fixtures stay synthetic.
- No test touches the network. Monkeypatch `_endpoint`, the page fetchers and `input`.
- **Settings are read at call time.** Modules do `from pipeline import settings` and read `settings.X` inside functions. Function parameters that used to default to a constant (`delay: float = REQUEST_DELAY_SECONDS`) become `delay: float | None = None`, resolved to `settings.<SOURCE>_DELAY_SECONDS` inside the body. This lets tests monkeypatch `settings` and lets callers pass explicit values.
- Precedence: CLI option > menu answer > `settings.py`.
- Default values (exact): `CURRENT_SEASON = None`, `SEASONS = range(2017, 2027)`, `SEASON_TYPE = "both"`, `DEFAULT_SOURCES = ("nba_stats", "bbref", "bbref_team", "darko")`, `BBREF_WITH_WEB_SCRAPER = False`, `DARKO_EVERY_DAYS = 7`, `NBA_STATS_TABLES = ()`, `NBA_STATS_DELAY_SECONDS = 1.5`, `BBREF_DELAY_SECONDS = 4`, `DARKO_DELAY_SECONDS = 3`, `TEAM_STATS_EXCEL = True`, `EXPORT_AFTER_RUN = False`, `QUALIFY_MINUTES = {"regular": 500, "playoffs": 100}`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Updating the current season when every file is already on disk.** Current-season tables are season-to-date snapshots, so menu option 1 must re-download them, not offer "Download again? [y/N]". Pinned by `test_update_current_season_always_refreshes` (Task 10).
2. **A one-item `DEFAULT_SOURCES` written without the trailing comma** (`("nba_stats")` is a str). `validate()` must reject it with a message that mentions the trailing comma. Pinned by `test_validate_rejects_string_sources` (Task 3).
3. **DARKO requested for a season whose nba_stats game logs are missing.** Today `darko.pull_season` crashes with `IndexError` on `chosen[0]`. It must report a failure that says to pull nba_stats first. Pinned by `test_darko_pull_without_game_logs_reports_failure` (Task 4).
4. **Ctrl+C or end-of-input during the menu.** The menu should print "Cancelled." and exit 1, not dump a traceback. Pinned by `test_menu_cancel_exits_cleanly` (Task 10).
5. **A season after the current one, such as 2027 in October 2026.** It would write empty tables that `--skip-existing` later treats as done. `ask_seasons` must reject anything above `current_season()`. Pinned by `test_ask_seasons_rejects_future_season` (Task 9).

## Decisions this plan makes that the spec leaves open

- **Menu option 1 has no have/expected check.** It shows one confirmation ("Update 2025-26? Replaces N files, about M minutes [Y/n]") and pulls nba_stats, bbref and bbref_team in full. DARKO uses `--skip-existing` because snapshots are immutable by date. The spec said options 1 to 4 all run the check; for option 1 that would default to not updating (Review Focus 1).
- `parse_seasons` stays in `pipeline/etl/orchestrator.py`, which is its current home and where the tests import it from.
- `pipeline/etl/orchestrator.py` gains `build_parser() -> argparse.ArgumentParser`, extracted from `main`, so the menu can print help when there is no TTY.
- `bbref_team` skips the page fetch when `--skip-existing` is set and all four CSVs for the season exist.
- The menu pulls several sources by calling `main()` once per source, in `DEFAULT_SOURCES` order.

---

## PR 1: folder restructure (branch `chore/restructure`, already created from `main`; the spec is committed there)

### Task 1: Move folders and rewrite code paths

**Files:**
- Move (git mv):
  - `scripts/` → `pipeline/`
  - `fetch_team_stats.py` → `pipeline/fetch_team_stats.py`
  - `start_nba_sources.py` → `pipeline/start_nba_sources.py`
  - `NBA_Player_Evaluation_Metrics.md` and `player_evaluation_metrics.md` → `docs/metrics/`
  - `workspace_guide.html` → `docs/guides/`
  - submodules `basketball`, `basketball_reference_scraper`, `basketball_reference_web_scraper`, `nba-player-points-prediction`, `dgrubis.github.io` → `vendor/<same name>`
- Move (plain `mv`, git-ignored):
  - `db/sqlite/nba_analytics.db*` → `data/warehouse/`
  - `third_party/nba_api` and `third_party/flexviz` → `vendor/`
  - `recent 9-29 claude summary.txt` → `local_analysis/chat_exports/`
- Delete: `nba_analytics_pipeline/`, `IMPLEMENTATION_PLAN.md`, `.github/prompts/plan-beginnerFriendlyPythonSetup.prompt.md`. Remove the then-empty `.github/`, `db/`, `third_party/` and `Semantic Models/`.
- Modify:
  - `pipeline/etl/paths.py:7` (`DB_PATH`)
  - `pipeline/fetch_team_stats.py:32` (`WORKSPACE_ROOT = Path(__file__).resolve().parents[1]`)
  - `pipeline/start_nba_sources.py` (`ROOT = parents[1]`, `WDC_DIR = ROOT / "vendor" / "dgrubis.github.io"`)
  - every `scripts.etl` import under `pipeline/`
  - `pytest.ini`, `.vscode/settings.json`, `bootstrap.cmd`, `demo_pipeline.cmd`, `.gitignore`, `requirements.txt`

- [ ] **Step 1: Record the baseline.** Run `python -m pytest -q` on the current tree. Expected: `87 passed`.
- [ ] **Step 2: Close anything holding the warehouse** (notebook kernels, DB browsers). Then move the git-ignored files:

```bash
mkdir -p data/warehouse vendor local_analysis/chat_exports
mv db/sqlite/nba_analytics.db* data/warehouse/ && rmdir db/sqlite db
mv third_party/nba_api third_party/flexviz vendor/ && rmdir third_party
mv "recent 9-29 claude summary.txt" local_analysis/chat_exports/
rmdir "Semantic Models"
```

- [ ] **Step 3: Run the `git mv` moves and deletions.** Use `git mv <submodule> vendor/<submodule>` once per submodule; it rewrites `.gitmodules` paths. Run `git rm -r nba_analytics_pipeline IMPLEMENTATION_PLAN.md .github`.
- [ ] **Step 4: Commit the moves alone.** Message: `Move code to pipeline/, repos to vendor/, docs to docs/`. Tests are expected to fail at this commit, because imports still say `scripts`.
- [ ] **Step 5: Rewrite references in code and config.** `git grep -lE "scripts\.etl|scripts/" -- pipeline pytest.ini .vscode '*.cmd' requirements.txt` lists the files. Replace `scripts.etl` with `pipeline.etl`, `scripts/tests` with `pipeline/tests`, `scripts/etl` with `pipeline/etl`, and `scripts/model` with `pipeline/model`. In `.gitignore`:
  - `db/sqlite/*.db` becomes `data/warehouse/*.db`
  - `third_party/nba_api/` and `third_party/flexviz/` become `vendor/nba_api/` and `vendor/flexviz/`
  - delete the `/recent *claude summary.txt` block

  Set `DB_PATH = PROJECT_ROOT / "data" / "warehouse" / "nba_analytics.db"`. In `requirements.txt`, change the scraper install line to `pip install -e vendor/basketball_reference_web_scraper -e vendor/basketball_reference_scraper`.
- [ ] **Step 6: Reinstall the editable scrapers.** Run `pip install -e vendor/basketball_reference_web_scraper -e vendor/basketball_reference_scraper`, then `python -c "import basketball_reference_scraper, basketball_reference_web_scraper"`. Expected: no output, exit 0.
- [ ] **Step 7: Run the tests.** `python -m pytest -q`. Expected: `87 passed`.
- [ ] **Step 8: Check that the warehouse is found and nothing reloads.** Run `python -m pipeline.etl.orchestrator ingest`. Expected: every file line reads `skipped` (already loaded by content hash), and the exit code is 0.
- [ ] **Step 9: Check the submodules.** Run `git submodule status`. Expected: 5 lines with `vendor/` paths and the same SHAs as before (`2225e08`, `c2bba94`, `1ec892d`, `04664004`, `c5f11c2`).
- [ ] **Step 10: Commit.** Message: `Point code, config and launchers at the new layout`.

### Task 2: Update docs, skills and local notebooks; final PR 1 checks

**Files:**
- Modify: `README.md`, `CREDITS.md`, `docs/guides/workspace_guide.html`, `.claude/skills/exploring-nba-tables/SKILL.md`, `.claude/skills/pulling-nba-data/SKILL.md`, `.claude/skills/writing-nba-queries/SKILL.md`, `.claude/skills/writing-nba-queries/template.py`
- Modify, local only and never committed: every `local_analysis/` file matching `scripts\.etl|db/sqlite|"db" / "sqlite"`. Today that is `darko_decomposition.py`, `eda.ipynb`, `player_profile.ipynb`, `player_profile.backup.ipynb` and `#season range.py`.

- [ ] **Step 1: Rewrite paths in the docs and skills.**
  - Apply the same replacements as Task 1, plus:
    - `db/sqlite/` → `data/warehouse/`
    - `python fetch_team_stats.py` → `python -m pipeline.fetch_team_stats`
    - each bare submodule folder name used as a path → `vendor/<name>`
    - the metric doc links → `docs/metrics/...`
  - Rewrite the README "Workspace Structure" list to match the spec's target layout, including a line for `local_analysis/` (private, git-ignored).
  - `template.py` must take its database path from `from pipeline.etl.paths import DB_PATH` rather than a string literal.
- [ ] **Step 2: Check for stale references.** Run `git grep -nE "scripts[./]|db/sqlite|third_party" -- . ':!docs/superpowers'`. Expected: no output.
- [ ] **Step 3: Update `local_analysis/`.** Make the same replacements in the five local files. In notebooks, replace the path parts `"db" / "sqlite"` with `"data" / "warehouse"`. Then run `python local_analysis/run_profile.py jokicni01 --profile --season 2026 --regular`. Expected: it writes `local_analysis/reports/profile_jokicni01_2026_regular.html` without `no such table` or `StopIteration`.
- [ ] **Step 4: Check the launcher.** Run `cmd //c demo_pipeline.cmd` from Git Bash. Expected: it finishes with no `FAILED` lines.
- [ ] **Step 5: Commit** (docs and skills only; `git status` must show nothing under `local_analysis/`). Message: `Update docs and skills for the new layout`.
- [ ] **Step 6: Open PR 1.** Run `gh pr create --base main`. The body lists the verification results from Task 1 Steps 6 to 9 and Task 2 Steps 2 to 4. It also includes this rollback: `git revert <merge>`, `mv data/warehouse/nba_analytics.db* db/sqlite/`, and reinstall the scrapers from their old root paths. End the body with the Claude Code attribution line.

---

## PR 2: settings, menu and cleanup (branch `feature/pipeline-settings`, created from `main` after PR 1 merges)

### Task 3: `pipeline/settings.py`, `validate()` and `current_season()`

**Files:**
- Create: `pipeline/settings.py`
- Modify: `pipeline/etl/paths.py`. Its base folders come from `settings`, and the `PROJECT_ROOT`, `DB_PATH`, `RAW_DIR` and `CLEAN_DIR` names stay.
- Test: `pipeline/tests/test_settings.py`

**Interfaces:**
- Produces:
  - module constants as in Global Constraints, plus `PROJECT_ROOT: Path`, `DATA_DIR`, `RAW_DIR`, `CLEAN_DIR`, `TABLEAU_DIR` and `WAREHOUSE_PATH: Path`
  - `class SettingsError(ValueError)`
  - `validate() -> None`, which raises `SettingsError` with a message starting with the setting name
  - `current_season(today: date | None = None) -> int`
  - `SOURCE_CHOICES = ("nba_stats", "bbref", "bbref_team", "darko")`
  - `SEASON_TYPES = ("regular", "playoffs", "both")`
  - `FIRST_NBA_STATS_SEASON = 1997`

- [ ] **Step 1: Write the failing tests.**

```python
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
```

- [ ] **Step 2: Run them to see them fail.** `python -m pytest pipeline/tests/test_settings.py -q`. Expected: `ModuleNotFoundError: pipeline.settings`.
- [ ] **Step 3: Write `pipeline/settings.py`.**
  - Group the settings under the spec's headings: Seasons, Sources, Request pacing, Team tables, Exports, Folders.
  - Every constant gets a comment covering what it does, the allowed values, and the cost or risk.
    - Copy the cost and risk notes verbatim from the spec's settings table. That includes the HTTP 429 warning on `BBREF_DELAY_SECONDS` and the DARKO local-use note on `DEFAULT_SOURCES`.
  - The header comment says the model settings live in `pipeline/model/config.py`.
  - `current_season`: return `settings.CURRENT_SEASON` if set. Otherwise return `today.year + 1` if `(month, day) >= (11, 1)`, else `today.year`.
  - `validate` imports `ALL_TABLES` and `TEAM_REQUEST_TABLES` inside the function, to avoid a circular import through `paths`.
    - The `SEASONS` and `CURRENT_SEASON` floor of 1997 applies only when `"nba_stats"` is in `DEFAULT_SOURCES`.
    - Delays other than `BBREF_DELAY_SECONDS` must be ≥ 0, and `BBREF_DELAY_SECONDS` must be ≥ 3.
- [ ] **Step 4: Have `paths.py` re-export the settings folders** (`DB_PATH = settings.WAREHOUSE_PATH` and so on). Run `python -m pytest -q`. Expected: all pass (87 + new).
- [ ] **Step 5: Commit.** Message: `Add pipeline/settings.py with validation and current_season`.

### Task 4: Wire settings into the extractors, exporter and orchestrator

**Files:**
- Modify:
  - `pipeline/etl/sources/nba_stats/extract.py` (`pull_season` and `pull_team_tables`: `delay: float | None = None`; `tables=None` falls back to `settings.NBA_STATS_TABLES or all`)
  - `pipeline/etl/sources/basketball_reference/extract.py` (all three pull functions: `delay: float | None = None`)
  - `pipeline/etl/sources/darko/extract.py` (`pull_dates`: `delay: float | None = None`; `pull_season`: `every_days: int | None = None`)
  - `pipeline/etl/export_csvs.py` (read `settings.QUALIFY_MINUTES` where `QUALIFY_MINUTES` was)
  - `pipeline/etl/orchestrator.py` (call `settings.validate()` at the top of `main`; `--season-type` default comes from `settings.SEASON_TYPE`; `--with-web-scraper` is true by default when `settings.BBREF_WITH_WEB_SCRAPER` is set; extract `build_parser()`)
- Delete the module constants `REQUEST_DELAY_SECONDS` in the three extractors and `QUALIFY_MINUTES` in `export_csvs.py`. Leave a one-line comment on fixed definitions such as `OFFENSIVE_PLAY_TYPES`, `TRACKING_MEASURES`, `CLOSEST_DEFENDER_RANGES` and `SHOT_CLOCK_RANGES`: `# Fixed: describes what stats.nba.com offers; not a setting.`
- Test: `pipeline/tests/test_settings_wiring.py`

**Interfaces:**
- Consumes: Task 3 `settings`.
- Produces: `orchestrator.build_parser() -> argparse.ArgumentParser`. The extractor functions keep their names; only the `delay` and `every_days` defaults change.

- [ ] **Step 1: Write the failing tests.**
  - `test_nba_pull_uses_settings_delay`: monkeypatch `settings.NBA_STATS_DELAY_SECONDS = 0.25`, monkeypatch `time.sleep` in the nba extract module to record its argument, and use the existing `_FakeEndpoint` pattern from `test_pulling.py`. Call `pull_season(2020, tables=[two tables], out_root=tmp_path)`. Assert `0.25` was recorded.
  - `test_nba_pull_uses_settings_tables`: monkeypatch `settings.NBA_STATS_TABLES = ("player_season_totals",)`. Call `pull_season(2020, out_root=tmp_path, delay=0)` with no `tables`. Assert the written names are `["player_season_totals.json"]`. Monkeypatch `pull_team_tables` to return an empty `PullReport`.
  - `test_percentiles_use_settings_qualify_minutes`: build the fixture warehouse with `run_pipeline(..., export_dir=tmp_path)`, monkeypatch `settings.QUALIFY_MINUTES = {"regular": 10**6, "playoffs": 10**6}`, and assert `player_season_percentiles(conn)` is empty.
  - `test_cli_season_type_defaults_to_settings`: monkeypatch `settings.SEASON_TYPE = "playoffs"`. Assert `build_parser().parse_args(["pull", "--source", "nba_stats"]).season_type == "playoffs"`.
  - `test_main_rejects_invalid_settings`: monkeypatch `settings.SEASON_TYPE = "x"`. `main(["features"])` raises `SettingsError`.
  - `test_darko_pull_without_game_logs_reports_failure`: `darko.pull_season(2019, raw_root=tmp_path, out_root=tmp_path / "darko")` returns a `PullReport` whose single `failed` entry mentions `"pull nba_stats"`.
- [ ] **Step 2: Run them to see them fail.** `python -m pytest pipeline/tests/test_settings_wiring.py -q`. Expected: 6 failures.
- [ ] **Step 3: Implement the wiring** as described in Files. In `darko.pull_season`, when `game_dates` returns no dates, return `PullReport(failed=[(f"darko {season}", f"no nba_stats team game logs for {season}; pull nba_stats for {season} first")])`.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** Message: `Read pull delays, tables and qualifying minutes from settings`.

### Task 5: Read `2025-26` as a season label

**Files:**
- Modify: `pipeline/etl/orchestrator.py` (`parse_seasons`)
- Test: `pipeline/tests/test_pulling.py`

**Interfaces:**
- Produces: `parse_seasons(values: list[str]) -> list[int]` (same signature). It raises `ValueError` on unreadable input or a descending range.

- [ ] **Step 1: Write the failing test.**

```python
@pytest.mark.parametrize("values, expected", [
    (["2026"], [2026]), (["2025-26"], [2026]), (["2025-2026"], [2025, 2026]),
    (["2017-2025"], list(range(2017, 2026))), (["2010-2012", "2026"], [2010, 2011, 2012, 2026]),
    (["2010-2012,", "2025-26"], [2010, 2011, 2012, 2026]),
])
def test_parse_seasons_labels_and_ranges(values, expected):
    assert parse_seasons(values) == expected

@pytest.mark.parametrize("bad", [["2025-2017"], ["abc"], ["2025-7"]])
def test_parse_seasons_rejects(bad):
    with pytest.raises(ValueError):
        parse_seasons(bad)
```

- [ ] **Step 2: Run it to see it fail.** `python -m pytest pipeline/tests/test_pulling.py -q`. Expected: the `2025-26` case returns `[]`.
- [ ] **Step 3: Implement.** Strip trailing commas. `\d{4}-\d{2}` is a label (end year = first + 1, and the two digits must equal `(first + 1) % 100`). `\d{4}-\d{4}` is an inclusive range that must ascend. `\d{4}` is one season. Anything else raises `ValueError` naming the value.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** Message: `Read 2025-26 as one season instead of an empty range`.

### Task 6: `bbref_team` pull source; retire `fetch_team_stats.py`

**Files:**
- Create: `pipeline/etl/sources/basketball_reference/team_extract.py`, containing the logic moved from `pipeline/fetch_team_stats.py`: `TABLES`, `SHEETS`, `fetch_season_page`, `parse_table`, `build_all_stats` and `write_workbook`
- Create: `pipeline/tests/fixtures/pages/NBA_2026_team.html`. A synthetic page with the four table ids (`per_poss-team`, `per_poss-opponent`, `totals-team`, `totals-opponent`), two teams each (one with a trailing `*`), a `League Average` row, and one table wrapped in `<!-- -->`.
- Modify: `pipeline/etl/orchestrator.py` (`--source` choices gain `bbref_team`; `_pull` branch)
- Delete: `pipeline/fetch_team_stats.py`
- Test: `pipeline/tests/test_team_extract.py`

**Interfaces:**
- Produces:
  - `pull_team_tables(season: int, out_root: Path | None = None, excel_dir: Path | None = None, excel: bool | None = None, skip_existing: bool = False, fetch_page: Callable[[int], str] | None = None) -> PullReport`
  - Defaults: `out_root = settings.RAW_DIR`, `excel_dir = settings.TABLEAU_DIR`, `excel = settings.TEAM_STATS_EXCEL`, `fetch_page = fetch_season_page`
  - It writes `{out_root}/{team,opponent}_{totals,per_100_poss}_{season}.csv`, plus `team_stats_{season}.xlsx` when `excel` is set
  - CLI: `pull --source bbref_team --season ...` sleeps `settings.BBREF_DELAY_SECONDS` between seasons

- [ ] **Step 1: Write the failing tests.**
  - `test_team_pull_writes_four_csvs`: with `fetch_page=lambda s: FIXTURE.read_text()` and `excel=False`, the written names equal `{"team_totals_2026.csv", "opponent_totals_2026.csv", "team_per_100_poss_2026.csv", "opponent_per_100_poss_2026.csv"}`. Each CSV has 2 rows, and the starred team has `Playoffs == True` and no `*` in its name.
  - `test_team_pull_output_ingests`: `TeamSeasonAdapter().discover(tmp_path)` finds the 4 files, and parsing them through the existing adapter with the conftest resolver produces no failures.
  - `test_team_pull_skip_existing_skips_fetch`: with the 4 CSVs present and `skip_existing=True`, a `fetch_page` that raises is never called, and `report.skipped` has 4 paths.
  - `test_team_pull_excel_optional`: with `excel=True`, `team_stats_2026.xlsx` exists in `excel_dir` and has an `All_Stats` sheet.
- [ ] **Step 2: Run them to see them fail.** `python -m pytest pipeline/tests/test_team_extract.py -q`. Expected: import error.
- [ ] **Step 3: Implement** `team_extract.py` and the `_pull` branch. Then delete `pipeline/fetch_team_stats.py` and update the docstrings in `team_season.py` and `schema.py` that name it.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass. Also run `git grep -n fetch_team_stats -- pipeline`. Expected: no output. README and skill mentions are fixed in Task 13.
- [ ] **Step 5: Commit.** Message: `Pull team and opponent tables with --source bbref_team`.

### Task 7: Download inventory

**Files:**
- Create: `pipeline/etl/sources/inventory.py`
- Test: `pipeline/tests/test_inventory.py`

**Interfaces:**
- Consumes: `nba_stats.extract.ALL_TABLES`, `TEAM_REQUEST_TABLES`, `raw_path` and `team_raw_path`; `basketball_reference.player_season.PLAYER_PAGES`; `team_extract.TABLES`; `canonical.teams.FRANCHISES`
- Produces:
  - `@dataclass(frozen=True) class Inventory: source: str; season: int; have: int; expected: int | None`
    - property `status -> Literal["none", "partial", "all"]`; `expected=None` gives `"partial"` whenever `have > 0`
  - `inventory(source: str, season: int, season_type: str = "regular", raw_root: Path | None = None) -> Inventory`
    - `season_type="both"` counts regular and playoff files together
    - `raw_root` defaults to `settings.RAW_DIR`
  - Expected counts:
    - nba_stats: `(len(ALL_TABLES) + len(FRANCHISES) * len(TEAM_REQUEST_TABLES)) × number of season types`
    - bbref: `len(PLAYER_PAGES)`
    - bbref_team: `4`
    - darko: `None`, with `have` = the number of `dpm_*.json` files under `darko/<season>/`

- [ ] **Step 1: Write the failing tests.**
  - `test_nba_inventory_counts_regular_and_playoffs`: in `tmp_path`, write 3 regular league files, 2 playoff league files and 1 regular `shot_chart/BOS.json`. With `n = len(ALL_TABLES) + 30 * len(TEAM_REQUEST_TABLES)`:
    - `"regular"` gives `have == 4` and `expected == n`
    - `"playoffs"` gives `have == 2`
    - `"both"` gives `have == 6` and `expected == 2 * n`
  - `test_bbref_team_inventory_all`: with 4 CSVs present, `status == "all"`.
  - `test_darko_inventory_has_no_expected`: with 2 snapshots, `expected is None` and `status == "partial"`; with 0 snapshots, `status == "none"`.
- [ ] **Step 2: Run them to see them fail.** Expected: import error.
- [ ] **Step 3: Implement** `inventory()` using the path helpers listed under Consumes, so the counts can't drift from what the pulls write.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** Message: `Report what each source already has on disk`.

### Task 8: Optional export after `run`

**Files:**
- Modify: `pipeline/etl/orchestrator.py`. `run_pipeline(..., export: bool | None = None)`, where `None` means `settings.EXPORT_AFTER_RUN`; `"exports"` is `0` when skipped. Add a `run --export` flag (`store_const`, `const=True`, default `None`).
- Modify: `pipeline/tests/test_orchestrator.py`. The tests that check exported files pass `export=True`.
- Test: `pipeline/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests.**
  - `test_run_without_export_writes_nothing`: with `settings.EXPORT_AFTER_RUN = False`, `run_pipeline(db, raw_root=raw_root, export_dir=clean)` leaves `clean` missing or empty, and `result["exports"] == 0`.
  - `test_run_export_flag`: `main(["--db", str(db), "run", "--export"])` with `RAW_DIR` and `CLEAN_DIR` monkeypatched to tmp paths writes `dim_stat.csv`.
  - `test_run_export_setting`: with `settings.EXPORT_AFTER_RUN = True`, `run_pipeline` writes `dim_stat.csv`.
- [ ] **Step 2: Run them to see them fail.** Expected: `test_run_without_export_writes_nothing` fails, because `run` exports today.
- [ ] **Step 3: Implement** the change. Update the module docstring line for `run`.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** Message: `Make CSV export after run optional`.

### Task 9: Prompts

**Files:**
- Create: `pipeline/prompts.py`
- Test: `pipeline/tests/test_prompts.py`

**Interfaces:**
- Consumes: `orchestrator.parse_seasons`, `settings.current_season`, `settings.FIRST_NBA_STATS_SEASON`, `canonical.dates.season_label`
- Produces (every function takes `ask: Callable[[str], str] = input` and `say: Callable[[str], None] = print`):
  - `ask_seasons(default: str, minimum: int = FIRST_NBA_STATS_SEASON, ask=input, say=print) -> list[int]`
  - `ask_yes_no(question: str, default: bool, ask=input, say=print) -> bool`
  - `ask_choice(question: str, options: dict[str, str], default: str, ask=input, say=print) -> str` returns the chosen key
  - `ask_date(question: str, default: str | None = None, ask=input, say=print) -> date`
- Copy the wording from the `local_analysis` season-range prototype: `"Seasons by end year, 2026 = 2025-26 [{default}]: "`, `"  Couldn't read {answer!r}. Try 2026 or 2017-2025."`, `"  Seasons must be between {minimum} and {current}."`, `"  Please answer y or n."` and the `"  -> N season(s): A to B"` echo.

- [ ] **Step 1: Write the failing tests.** A helper `answers(*xs)` returns an `ask` that pops scripted answers.
  - `test_ask_seasons_reprompts_then_accepts`: answers `("abc", "2017-2019")` give `[2017, 2018, 2019]`, and `say` was called with the "Couldn't read" text.
  - `test_ask_seasons_enter_takes_default`: `("",)` with `default="2025-26"` gives `[2026]`.
  - `test_ask_seasons_rejects_future_season`: with `settings.current_season` monkeypatched to return 2026, answers `("2027", "2026")` give `[2026]`, and the "between" message was shown.
  - `test_ask_yes_no`: `("maybe", "Y")` gives `True`; `("",)` with `default=False` gives `False`.
  - `test_ask_choice`: `("9", "2")` over `{"1": ..., "2": ...}` gives `"2"`.
  - `test_ask_date_rejects_bad_format`: `("11/01/2025", "2025-11-01")` gives `date(2025, 11, 1)`.
- [ ] **Step 2: Run them to see them fail.** Expected: import error.
- [ ] **Step 3: Implement.** Each function loops until the answer is valid. `ask_seasons` checks that the parsed list is non-empty and within `[minimum, current_season()]`. A `ValueError` from `parse_seasons` triggers the "Couldn't read" message.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** Message: `Add reusable season, yes/no, choice and date prompts`.

### Task 10: The `python -m pipeline` menu and `nba.cmd`

**Files:**
- Create: `pipeline/__main__.py`, `pipeline/menu.py`, `nba.cmd`
- Delete: `bootstrap.cmd`, `demo_pipeline.cmd`, `pipeline/etl/run_demo_pipeline.py`
- Test: `pipeline/tests/test_menu.py`

**Interfaces:**
- Consumes: Task 4 `build_parser` and `main`; Task 7 `inventory`; Task 9 prompts; `settings`
- Produces:
  - `pull_argv(source: str, seasons: list[int], season_type: str, skip_existing: bool) -> list[str]`
    - e.g. `["pull", "--source", "nba_stats", "--season", "2017", "2018", "--season-type", "both", "--skip-existing"]`
    - `--season-type` is passed only for nba_stats
    - `--with-web-scraper` is added for bbref when `settings.BBREF_WITH_WEB_SCRAPER` is set
  - `run_menu(ask=input, say=print, run=orchestrator.main, is_tty: Callable[[], bool] = sys.stdin.isatty) -> int`
  - `pipeline/__main__.py` is `raise SystemExit(run_menu())`
- Menu text and options: exactly the spec's six options plus `q`. Before each `run(argv)`, `say("-> python -m pipeline.etl.orchestrator " + " ".join(argv))`.
- Option behavior:
  - **1, Update current season.** No inventory check. Ask once: `"Update {label}? Replaces about N files, about M minutes"` (default Y). Then pull every `DEFAULT_SOURCES` entry in order. nba_stats, bbref and bbref_team pull without `--skip-existing`; darko pulls with it.
  - **2, Backfill, and 4, DARKO.** For each source and each season, use `inventory()` and the spec's none/partial/all table to decide whether to pull and whether to pass `--skip-existing`. Option 2 asks seasons (default `SEASONS` as `"first-last"`), sources (default `DEFAULT_SOURCES`) and season type (default `SEASON_TYPE`). Option 4 prints `"DARKO data: use it locally; don't publish it."` first.
    - When darko is selected for a season with no nba_stats team game log on disk, and nba_stats is not also selected, say `"{label}: pull nba_stats for this season first; skipping DARKO."` and skip it.
  - **3, Daily box scores.** Ask the start and end dates, then run `["pull", "--source", "bbref", "--date", start, "--end", end]`.
  - **After any pull** (options 1 to 4), ask `"Load the new files into the warehouse now?"` (default Y). Yes runs `["run"]`, plus `"--export"` when `"Export CSVs too?"` (default `EXPORT_AFTER_RUN`) is yes.
  - **5, Rebuild warehouse.** Ask the export question, then run.
  - **6, Export CSVs.** Ask latest, one season or all seasons, then run `["export"]`, `["export", "--season", N]` or `["export", "--all-seasons"]`.
  - **No TTY:** print `build_parser().format_help()` and return 0.
  - **`KeyboardInterrupt` or `EOFError`** from any prompt: print `"Cancelled."` and return 1.
  - Call `settings.validate()` first. On `SettingsError`, print it and return 2.

- [ ] **Step 1: Write the failing tests.** Use scripted `ask`, a recording `run` that returns 0, `is_tty=lambda: True`, and `RAW_DIR` monkeypatched to a tmp folder populated per test.
  - `test_pull_argv_nba_stats`: `pull_argv("nba_stats", [2017, 2018], "both", True)` equals the example above.
  - `test_update_current_season_always_refreshes`: all nba_stats files exist for `current_season()`. Answers `("1", "", "n", "q")`. The recorded argv lists are one pull per default source, in `DEFAULT_SOURCES` order. The nba_stats pull has no `--skip-existing`; the darko pull has it.
  - `test_backfill_partial_uses_skip_existing`: some 2018 nba_stats files exist. Answers `("2", "2018", "nba_stats", "regular", "", "n", "q")`. Recorded: `pull_argv("nba_stats", [2018], "regular", True)`.
  - `test_backfill_all_present_defaults_to_skip`: all 2018 files exist. Answers `("2", "2018", "nba_stats", "regular", "", "q")`. No pull was recorded.
  - `test_darko_without_game_logs_is_skipped`: answers `("4", "2019", "q")`. No pull was recorded, and the "pull nba_stats" message was shown.
  - `test_export_choices`: answers `("6", "3", "q")` record `["export", "--all-seasons"]`.
  - `test_menu_without_tty_prints_help`: with `is_tty=lambda: False`, it returns 0, `say` output contains `"pull"`, and nothing was recorded.
  - `test_menu_cancel_exits_cleanly`: an `ask` that raises `EOFError` makes it return 1 and say `"Cancelled."`.
  - `test_menu_reports_invalid_settings`: with `settings.SEASON_TYPE = "x"`, it returns 2.
- [ ] **Step 2: Run them to see them fail.** Expected: import error.
- [ ] **Step 3: Implement** `pipeline/menu.py` and `pipeline/__main__.py`. `nba.cmd` contains:

```bat
@echo off
cd /d "%~dp0"
py -3 -m pipeline
if errorlevel 1 pause
```

- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass. Run `python -m pipeline < /dev/null`. Expected: the orchestrator help text and exit 0.
- [ ] **Step 5: Commit.** Message: `Add python -m pipeline menu and nba.cmd launcher`.

### Task 11: Source template and guide

**Files:**
- Create: `pipeline/etl/sources/_template/__init__.py`, `pipeline/etl/sources/_template/extract.py`, `pipeline/etl/sources/_template/adapter.py`, `docs/guides/adding-a-source.md`
- Test: `pipeline/tests/test_template.py`

**Interfaces:**
- Produces:
  - `TemplateAdapter` with `source_name = "template"` and `source_system = "template"`
  - `discover(self, raw_root: Path) -> list[RawFile]` returns `[]` until filled in
  - `parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult`
  - `extract.pull_season(season: int, out_root: Path | None = None, delay: float | None = None, skip_existing: bool = False) -> PullReport`, which raises `NotImplementedError("FILL IN: ...")`
- It is not registered in `registry.py`.

- [ ] **Step 1: Write the failing test.** `test_template_matches_adapter_contract` imports `TemplateAdapter` and asserts it has `source_name`, `source_system`, `discover` and `parse`, that `discover(tmp_path) == []`, and that `"template" not in ADAPTERS`.
- [ ] **Step 2: Run it to see it fail.** Expected: import error.
- [ ] **Step 3: Write the template.**
  - Mark each decision point with `# FILL IN:`: request URL and params, raw file name pattern, the `discover` glob, the canonical table and row mapping in `parse`, and the `resolver.team(...)` / `resolver.player(...)` calls. Each comment points at a real example in `darko/` or `basketball_reference/team_season.py`.
  - Write `docs/guides/adding-a-source.md`. Cover the four steps from the README's "Adding a new source adapter": copy `_template/`, add the registry line (and `SOURCE_PRECEDENCE` if the source competes with others), add the settings entries (`<NAME>_DELAY_SECONDS` and default sources), and add the fixture and test.
  - The README section links to the guide.
- [ ] **Step 4: Run all tests.** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** Message: `Add a copyable source template and adding-a-source guide`.

### Task 12: Remove dead ETL modules

**Files:**
- Delete: `pipeline/etl/live_ingest.py`, `pipeline/etl/historical_ingest.py`, `pipeline/etl/sample_backfill.py`, `pipeline/etl/normalize.py`

- [ ] **Step 1: Confirm nothing uses them.** Run `git grep -nE "live_ingest|historical_ingest|sample_backfill|etl\.normalize|from \.normalize|from \.\.normalize" -- . ':!docs/superpowers'`. Expected: hits only inside the four files themselves. If anything else appears, keep that file and note it in the PR.
- [ ] **Step 2: Delete them.** Run `python -m pytest -q`. Expected: all pass.
- [ ] **Step 3: Commit.** Message: `Remove unused first-draft ETL modules`.

### Task 13: Docs for PR 2, final checks, PR

**Files:**
- Modify: `README.md` ("Running the pipeline" leads with `python -m pipeline` / `nba.cmd`, then the CLI; `run --export`; `pull --source bbref_team`; a link to `pipeline/settings.py`; the "Adding a new source adapter" section links the guide), `.claude/skills/pulling-nba-data/SKILL.md` (same commands; DARKO is a default source and is pulled after nba_stats), `.claude/skills/exploring-nba-tables/SKILL.md` (exports need `run --export`), `docs/guides/workspace_guide.html`

- [ ] **Step 1: Update the docs** as listed. Then run `git grep -nE "fetch_team_stats|demo_pipeline|bootstrap\.cmd|run_demo_pipeline" -- . ':!docs/superpowers'`. Expected: no output.
- [ ] **Step 2: Run the full suite.** `python -m pytest -q`. Expected: all pass, with a count above 87.
- [ ] **Step 3: Check the real warehouse.** Run `python -m pipeline.etl.orchestrator ingest`. Expected: every file is skipped, exit 0. The warehouse is unaffected by PR 2.
- [ ] **Step 4: Try the menu by hand.** Run `python -m pipeline` and choose `6`, then `1` (latest). Expected: the printed `->` command, then `exported N files`. Quit with `q`.
- [ ] **Step 5: Commit**, then open PR 2 with `gh pr create --base main`. List the test count and the Step 3 and 4 results in the body, and end it with the Claude Code attribution line.

---

## After both PRs merge (Task 14, user-run steps included)

- [ ] **Step 1: Rebase the residual-model branch.** Run `git switch feature/residual-model && git rebase main`.
- [ ] **Step 2: Update its spec and plan paths.** In `docs/superpowers/specs/2026-10-08-residual-model-walk-forward-design.md` and `docs/superpowers/plans/2026-10-09-residual-model-walk-forward.md`, replace `scripts/model` with `pipeline/model`, `scripts.model` with `pipeline.model`, `scripts/tests` with `pipeline/tests`, and `scripts.etl` with `pipeline.etl`. Add to plan Task 1 that `pipeline/model/config.py`'s header comment says pipeline settings live in `pipeline/settings.py`. Check with `git grep -n "scripts[./]" docs/superpowers/*/2026-10-0[89]-residual*`; expected: no output. Commit with `Point residual-model docs at pipeline/`.
- [ ] **Step 3: Playoff backfill (user, about 1 to 1.5 hours of network).** Run `python -m pipeline`, choose `2`, enter seasons `2017-2025`, sources default, season type `playoffs`, then load into the warehouse. Expected: the pull summary shows playoff files written for 2017 to 2025 with no `FAILED` lines, and `select distinct season from fact_player_season_stat where season_type = 'playoffs'` returns 2017 to 2026.
