# Credits and project inspiration

## Project ownership

This repository was created and organized by Abhinav Nalluri as a personal NBA analytics and decision-support project.

Portfolio project: NBA player data project
GitHub: @analluri229-cmd

The goal is to combine open sports data, custom evaluation logic, and a reproducible pipeline into a single workspace for exploring player performance, team context, and decision intelligence.

## Key inspirations and sources

This project is inspired by and relies on public basketball data sources and prior open-source work, including:

- Basketball Reference
  - Historical player, team, and game context
  - Season totals and box score data
  - Public stat conventions used widely across basketball analysis

- stats.nba.com
  - Official NBA stats feeds
  - Game logs, player stat tables, and team-level data

- DARKO (www.darko.app), by Kostya Medvedovsky (@kmedved) and Andrew Patton (@anpatt7)
  - Daily Plus-Minus (DPM) player ratings and projections, pulled as dated snapshots
  - DARKO data belongs to its authors; this project stores it for personal analysis only

- Open-source basketball data tooling and reference projects blended into this workspace
  - `basketball_reference_scraper/` — repository used for Basketball Reference extraction patterns and historical gathering utilities
  - `basketball_reference_web_scraper/` — web-scraping workflows and season/table extraction logic
  - `basketball/` — historical basketball data and source material used for broader reference work
  - `dgrubis.github.io/` — older NBA Stats Web Data Connector integration and related data-access experimentation
  - `nba-player-points-prediction/` — a separate analytics project used as a reference for player-focused analytical framing and scoring-style evaluation
  - `third_party/` — location for additional external or supporting data-source projects and experiment code

- Existing basketball analytics literature and metric frameworks
  - Player efficiency and valuation concepts from public basketball analytics work
  - Custom metric ideas captured in `NBA_Player_Evaluation_Metrics.md` and `player_evaluation_metrics.md`

## Repositories blended into this project

The following repositories and project folders were incorporated as part of the broader build environment for this project:

- `basketball_reference_scraper/`
- `basketball_reference_web_scraper/`
- `basketball/`
- `dgrubis.github.io/`
- `nba-player-points-prediction/`
- `nba_analytics_pipeline/`
- `third_party/`

These were used as reference material, analytical inspiration, extraction logic, and supporting source code in building the current pipeline. This project is a custom integration and extension of those ideas rather than an entirely new and isolated system.

## Why this project exists

This project is not meant to replace official league data or proprietary analysis products. It is a self-built, modular analytics exercise that turns multiple public data sources into a structured, versioned workflow for:

- player evaluation
- team and lineup context
- season trend analysis
- data exploration and dashboard preparation

## Attribution guidance

If you use or build on this project:

- credit the original data providers for the raw source data
- credit the open-source tooling and documentation that supported the build
- clearly identify this repo as a custom project implementation rather than an official NBA or league product

## Notable source repositories in this workspace

- `basketball_reference_scraper/` — Basketball Reference scraping tooling
- `basketball_reference_web_scraper/` — web scraping utilities and data extraction helpers
- `basketball/` — historical basketball data and source material
- `dgrubis.github.io/` — older NBA Stats WDC integration and related work
- `nba_analytics_pipeline/` — project-specific pipeline components

## Recommended citation

If you want to reference this project in a presentation, article, or portfolio, a simple attribution could read:

> This project was created as a personal NBA analytics and decision-intelligence pipeline, inspired by Basketball Reference, stats.nba.com, and open-source basketball data tooling. It combines public sports data with custom evaluation metrics and a reproducible data pipeline.
