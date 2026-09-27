# NBA Decision Intelligence ETL

This package is an internal ETL scaffold for building a Tableau-ready NBA analytics workflow.

It follows the cleaner architectural separation used by `basketball_reference_web_scraper`:

- `extract.py` handles raw data retrieval
- `transform.py` normalizes and enriches data
- `load.py` writes curated outputs to disk
- `metrics.py` contains custom decision-oriented metric logic
- `client.py` provides a high-level pipeline entry point

## Goal

The purpose is to combine:

- Basketball Reference data
- custom basketball metrics
- team context and decision signals
- Tableau semantic model input tables

This supports decisions around player performance, lineup value, productivity trends, and roster evaluation.

## Recommended pipeline flow

1. Extract player and team data for a selected season
2. Standardize fields into a consistent schema
3. Add custom metrics such as efficiency deltas, usage trends, and decision indicators
4. Save curated data as CSV/Parquet-ready files
5. Load into Tableau semantic models for dashboarding

## Example usage

```python
from nba_analytics_pipeline.client import run_pipeline

result = run_pipeline(
    season_end_year=2025,
    team_names=['GSW', 'BOS', 'DAL'],
    player_names=['Stephen Curry', 'Jayson Tatum']
)

print(result['player_snapshot'].head())
print(result['team_snapshot'].head())
```

## Output folders

The pipeline expects an output structure like:

- `data/raw/` for source pulls
- `data/clean/` for transformed data
- `data/tableau/` for Tableau-ready files

## Notes

This scaffold is intentionally modular so we can evolve it into a production-style ETL without locking the project into one scraper or one dashboard pattern.
