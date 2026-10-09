---
name: exploring-nba-tables
description: Use when looking up or exploring player, team, game, or shot statistics in this NBA workspace - finding a player's stats, comparing seasons, picking which CSV or warehouse table holds a stat, or reading what a stat column means.
---

# Exploring NBA Tables

## Two places the data lives

| | `data/clean/` CSVs | `data/warehouse/nba_analytics.db` |
|---|---|---|
| Seasons | **Latest season only (2026)** by default | **All loaded seasons, 2017-2026** |
| Shape | Wide: one column per stat | Long: one row per stat (`stat_name`, `value`) |
| Also has | - | `fact_shot` (x/y of every shot), `on_off`, `shot_context`, lineups |

Any question spanning seasons -> warehouse. Loading a CSV and seeing only 2026 is expected, not missing data.
Other exports: `export --season 2020` writes `data/clean/season_2020/`; `export --all-seasons` writes every season.

Seasons are labelled by end year: `2026` = 2025-26.

## Find a player

`player_id` is the Basketball-Reference slug (`jamesle01`). `nba_person_id` holds the stats.nba.com id.
Names keep their accents (`Luka Dončić`, `Nikola Jokić`), so strip them before searching:

```python
dim = pd.read_csv("data/clean/dim_player.csv")
plain = dim.player_name.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
dim[plain.str.contains("doncic", case=False)][["player_id", "player_name"]]
```

On Windows, printing accented names can raise `UnicodeEncodeError`; set `PYTHONIOENCODING=utf-8`.

## Rows per player-season

Every stat table has `season_type` (`regular`/`playoffs`) and `split`. `split = 'TOT'` is the full season; traded players also get one row per team. For one line per season, filter `season_type='regular' AND split='TOT'`.

## CSV lookup (latest season)

```python
import pandas as pd
df = pd.read_csv("data/clean/player_season/nba_stats_advanced.csv")
df[(df.player_id == "jamesle01") & (df.split == "TOT")][["season_type", "ts_pct", "usg_pct"]]
```

## Multi-season lookup (warehouse)

The long table has no stat columns - filter on `stat_name`, then pivot:

```python
import sqlite3, pandas as pd
con = sqlite3.connect("data/warehouse/nba_analytics.db")
df = pd.read_sql("""
    SELECT season, stat_name, value FROM fact_player_season_stat
    WHERE player_id = ? AND source_system = 'basketball_reference' AND stat_table = 'shooting'
      AND season_type = 'regular' AND split = 'TOT'
      AND stat_name IN ('fg_pct', 'fg_pct_fg3a', 'avg_dist')
""", con, params=["jamesle01"])
df.pivot(index="season", columns="stat_name", values="value")
```

`source_system` + `stat_table` match the CSV filename: `nba_stats_shot_zones.csv` = `('nba_stats', 'shot_zones')`.

## What a stat means

`data/clean/dim_stat.csv` (or `dim_stat` table): join on `source_system, stat_table, stat_name` to get `label`, `definition`, `unit`, `higher_is_better`. The warehouse table also has `entity` (`player`/`team`/`lineup`); add `entity = 'player'` or the join duplicates rows.

The same stat can have different names per table (3P% is `fg3_pct` in BBRef totals/per_game but `fg_pct_fg3a` in BBRef shooting). Find a stat by its label instead of guessing the column:

```python
ds = pd.read_csv("data/clean/dim_stat.csv")
hit = ds.label.str.contains("3-pt", regex=False) & ds.label.str.contains("FG%", regex=False)
ds[hit][["source_system", "stat_table", "stat_name", "label"]]   # search words, not a full label
```
Units: `fraction` 0.456 = 45.6%; `percent` 0-100; `index` 100 = league average; `rating` per 100 possessions.
League percentiles (latest season): `data/clean/analysis/player_season_percentiles.csv`.

## Shooting tables answer different questions

Each breaks shots down a different way (distance bands, court zones, point share) - pick by question rather than trying to reconcile their columns.

| Question | Table |
|---|---|
| FG% and shot mix by distance band (0-3, 3-10, 10-16, 16+ ft, 3PT), % assisted, dunks, corner 3s | `basketball_reference_shooting` |
| FG% relative to league average (100 = average), points added | `basketball_reference_adj_shooting` |
| Makes/attempts in 5-ft buckets | `nba_stats_shot_distance` |
| Restricted area, paint, mid-range, corner vs above-break 3 | `nba_stats_shot_zones` |
| Share of points from 2s/3s/FT/paint/fast break, assisted vs unassisted | `nba_stats_scoring` |
| Shot chart (x/y per attempt) | `fact_shot` (warehouse only) |

## Other tables

- Games: `data/clean/analysis/player_games.csv` (names joined), `fact_player_game`, `fact_team_game`
- Teams: `data/clean/analysis/team_seasons.csv`, `fact_team_season_box`
- Full column list: `pipeline/etl/canonical/schema.py`

Run from the project root, or the relative paths above won't resolve.
