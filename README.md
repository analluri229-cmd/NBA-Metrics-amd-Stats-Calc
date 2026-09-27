# NBA Player Performance & Decision Intelligence Pipeline

This workspace is set up to build a Python-based NBA analytics pipeline that blends:

- Basketball Reference data
- Custom player and team metrics
- Tableau-ready semantic models
- Executive-facing performance dashboards for NBA teams and decision makers

The goal is to help teams understand player performance, identify what is working, and support roster and game decisions through clear, actionable visual analytics.

## Project Objective

We want to combine public basketball statistics with custom business/decision metrics to answer questions like:

- Which players are performing above expectation?
- Which lineup combinations are creating the most value?
- Which players are improving, declining, or underutilized?
- What signals should a team use when deciding on rotation, trade, or contract decisions?

This will ultimately feed Tableau semantic models and dashboards for team-facing analysis.

## Workspace Structure

- `basketball_reference_scraper/` — installed Python package for Basketball Reference data extraction
- `Semantic Models/` — Tableau semantic model work and exported assets
- `.vscode/` — Python workspace settings and debugging config

## Installed Python Package

The project has been installed into the workspace virtual environment in editable mode.

Core package inspection shows the scraper contains key modules such as:

- `players.py` — player stats, game logs, headshots
- `teams.py` — team stats, roster, roster stats, team ratings
- `seasons.py` — schedules and standings
- `box_scores.py` — box score extraction
- `pbp.py` — play-by-play data
- `shot_charts.py` — shot chart data
- `injury_report.py` — injury reporting

This gives us a strong foundation for collecting NBA data at the player, team, and game level.

## Recommended Architecture

### 1. Data Extraction
Use the installed `basketball_reference_scraper` package to pull:

- player stats
- team stats
- game logs
- schedules
- standings
- box scores

### 2. Data Enrichment
Add custom metrics and logic, such as:

- efficiency above league average
- usage vs productivity
- lineup impact proxies
- trend analysis over time
- injury/load adjustments
- role-based player grouping

### 3. Data Normalization
Convert raw scraper outputs into a clean, analysis-ready schema:

- `player_id`
- `season`
- `team`
- `date`
- `games_played`
- `minutes`
- `usage_rate_proxy`
- `efficiency_metric`
- `custom_score`
- `decision_flag`

### 4. Tableau Semantic Models
Prepare final tables for Tableau such as:

- `fact_player_game`
- `fact_team_game`
- `dim_player`
- `dim_team`
- `dim_date`
- `fact_lineup_snapshot`

These can be used to build semantic layers that support:

- trend analysis
- player performance comparisons
- team decision-making dashboarding

## Example Python Usage

```python
from basketball_reference_scraper.players import get_stats, get_game_logs
from basketball_reference_scraper.teams import get_team_stats, get_roster_stats

# Example: player per-game stats
player_stats = get_stats('Stephen Curry', stat_type='PER_GAME')
print(player_stats.head())

# Example: team stats
team_stats = get_team_stats('GSW', 2025, data_format='PER_GAME')
print(team_stats)
```

## Planned Data Pipeline

1. Extract raw Basketball Reference data
2. Clean and standardize into pandas DataFrames
3. Merge with custom metric logic
4. Aggregate to game / player / team / season views
5. Export to CSV or parquet
6. Load into Tableau semantic model(s)
7. Build dashboards for teams and leadership

## Suggested Next Steps

1. Confirm the exact metrics and dimensions needed for your team analysis
2. Create a standard data model for player-game and team-game records
3. Build a Python ETL layer using pandas
4. Export curated datasets for Tableau
5. Create dashboards for:
   - player performance trends
   - team efficiency trends
   - player value and decision support
   - roster fit and opportunity analysis

## Notes

This project should remain modular and reproducible:

- keep raw extraction code separate from metric logic
- version the datasets and transformation logic
- document assumptions for each custom metric
- keep Tableau-ready outputs structured and consistent

## Working Goal

The eventual output should be a repeatable NBA analytics workflow that combines:

- trusted external basketball metrics
- proprietary team-context metrics
- Tableau-friendly semantic data model(s)
- clear visual storytelling for coaching and team decision-makers
