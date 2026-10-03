---
name: writing-nba-queries
description: Use when writing a reusable Python script or notebook of your own against this NBA workspace's data - a player or team report, a multi-season comparison, a chart, or any custom query you want to rerun.
---

# Writing Your Own NBA Queries

For which table or stat to use, see exploring-nba-tables. This skill covers the file itself.

## Where the file goes

`local_analysis/<name>.py` (or `.ipynb`). It's git-ignored because the repo is a public portfolio; `scripts/` is only for pipeline code. Save charts and reports under `local_analysis/output/`.

## Start from the template

Copy [template.py](template.py) to `local_analysis/`, change `STATS`, run:

```
python local_analysis/my_report.py "Luka Doncic" --chart
```

What it already handles, so keep it when you change things:

| Concern | How |
|---|---|
| Runs from any folder | paths built from `Path(__file__).resolve().parents[1]`, not the working directory |
| Can't damage the warehouse | read-only connection (`?mode=ro`) |
| Accents / partial names | exact match first, then accent-free contains; stops if 0 or 2+ players match |
| Traded players, playoffs | `split = 'TOT'` and one `season_type` per query |
| Windows console | `sys.stdout.reconfigure(encoding="utf-8")` |
| SQL injection / quoting | `?` parameters, never f-string values into SQL |

`STATS` maps your column name to `(source_system, stat_table, stat_name)`; find names in `data/clean/dim_stat.csv`.

## Pick one source per stat

`nba_stats` and `basketball_reference` both have most box and advanced stats. `nba_stats` rounds (TS% 0.594) where BBRef keeps full precision (0.59355), and a few stats are defined differently. Use one source for a given stat across all seasons so a trend line never mixes the two.
Playoffs: `basketball_reference` has 2017-2026; `nba_stats` only 2026 unless older playoffs are pulled (see pulling-nba-data).

## Running it

- Interpreter: the one in `.vscode/settings.json` (`C:/Users/themi/.venv`). It has pandas, matplotlib and the rest of `requirements.txt`.
- In VS Code: open the file, then Run Python File. Arguments go in the terminal command.
- Notebooks: `local_analysis/player_profile.ipynb` is a worked example that loads its data the same way.

## Keep private data private

Anything built from `fact_player_rating_daily` (DARKO) stays in `local_analysis/`, never in a committed file or a published chart. For a model, join each game to the latest rating dated **before** that game, or the rating leaks the result.
