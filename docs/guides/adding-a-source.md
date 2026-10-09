# Adding a data source

A source has two halves:

- **The extractor** (`extract.py`) downloads raw files and is the only code that touches the network.
- **The adapter** (`adapter.py`) turns one raw file into canonical rows and never touches the database.

The loader, the features and the exports already work with any adapter that keeps this contract.

A copyable skeleton lives in [`pipeline/etl/sources/_template/`](../../pipeline/etl/sources/_template/). Every place you need to decide something is marked `# FILL IN:`.

## 1. Copy the template

```
pipeline/etl/sources/_template/  ->  pipeline/etl/sources/<your_source>/
```

Rename `TemplateAdapter` and set its two names:

| Attribute | What it is | Example |
|---|---|---|
| `source_name` | this adapter's id, recorded for every file in `source_manifest` | `"darko"` |
| `source_system` | the data family, used when two sources supply the same row | `"basketball_reference"` |

## 2. Write the extractor (`extract.py`)

- Save each response **unmodified** under `data/raw/<your_source>/<season>/`. Name files so the adapter can tell the season and table from the path.
- Use `with_retries` for transient errors and raise `NotAvailable` for a table the source doesn't have. Return a `PullReport`, so `pull` can list what was written, skipped or failed.
- Add a delay setting to [`pipeline/settings.py`](../../pipeline/settings.py), e.g. `MYSOURCE_DELAY_SECONDS = 3`, with a comment on the site's limits. Read it inside your function (`settings.MYSOURCE_DELAY_SECONDS`), not at import time.
- Wire it into `pull` by adding a branch in `_pull` in [`pipeline/etl/orchestrator.py`](../../pipeline/etl/orchestrator.py) and the name to `--source` choices.
  - To include it in the menu's defaults, add it to `SOURCE_CHOICES` and `DEFAULT_SOURCES` in `settings.py`.
  - Then add a count to [`inventory.py`](../../pipeline/etl/sources/inventory.py), so the menu can tell what is already downloaded.

## 3. Write the adapter (`adapter.py`) and register it

- `discover(raw_root)` returns a `RawFile` for every file the extractor writes.
- `parse(raw, resolver)` returns rows with `result.add("<canonical table>", {...})`. The tables and their columns are in [`pipeline/etl/canonical/schema.py`](../../pipeline/etl/canonical/schema.py).
- Resolve every team with `resolver.team(...)` and every player with `resolver.player(...)`.
  - Players that can't be matched get a fallback id and land in `unresolved_entity` for review.
  - Fix them in `data/reference/player_xref_overrides.csv`.
- Register it in [`pipeline/etl/sources/registry.py`](../../pipeline/etl/sources/registry.py). Order matters: adapters that need another source's player matches go after it.
- If it competes with an existing source for the same rows, add its `source_system` to `SOURCE_PRECEDENCE` in `schema.py`.

## 4. Test it offline

- Put a small, trimmed real file (or a synthetic one, for data you may not publish) in `pipeline/tests/fixtures/raw/<your_source>/`.
- Add a parse test next to the others in `pipeline/tests/test_adapters.py`.
- For the extractor, monkeypatch the fetch so no test touches the network (see `test_pulling.py`).
- Run `python -m pytest`.

## 5. Load it

```
python -m pipeline.etl.orchestrator pull --source <your_source> --season 2026
python -m pipeline.etl.orchestrator ingest --source <adapter source_name>
```

Before downloading, check the source's terms of use. If its data is personal-use only, keep `data/raw/<your_source>/` git-ignored, and keep the data out of anything you publish.
