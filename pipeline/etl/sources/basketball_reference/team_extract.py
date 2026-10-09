"""Download team and opponent stat tables from a Basketball-Reference season page.

    python -m pipeline.etl.orchestrator pull --source bbref_team --season 2024-2026

One request per season (https://www.basketball-reference.com/leagues/NBA_<year>.html) yields:

    per_poss-team      Team per 100 possessions             -> team_per_100_poss_<season>.csv
    per_poss-opponent  Opponent per 100 possessions         -> opponent_per_100_poss_<season>.csv
    totals-team        Team season totals                   -> team_totals_<season>.csv
    totals-opponent    Opponent season totals               -> opponent_totals_<season>.csv

The CSVs go to data/raw/ (read by the bbref_team_season adapter). With settings.TEAM_STATS_EXCEL
the four tables also go to one Tableau workbook, data/tableau/team_stats_<season>.xlsx (one sheet
per table plus an "All_Stats" sheet that stacks them).
"""
from __future__ import annotations

import io
import re
import time
from pathlib import Path
from typing import Callable

import pandas as pd
import requests
from openpyxl.utils import get_column_letter

from pipeline import settings

from ..pulling import PullReport
from .extract import RateLimited

SEASON_URL = "https://www.basketball-reference.com/leagues/NBA_{season}.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# table id on the page -> output file stem
TABLES = {
    "per_poss-team": "team_per_100_poss",
    "per_poss-opponent": "opponent_per_100_poss",
    "totals-team": "team_totals",
    "totals-opponent": "opponent_totals",
}

# output file stem -> (Excel sheet name, Perspective, Stat_Basis)
SHEETS = {
    "team_per_100_poss": ("Team_Per100", "Team", "Per 100 Poss"),
    "opponent_per_100_poss": ("Opponent_Per100", "Opponent", "Per 100 Poss"),
    "team_totals": ("Team_Totals", "Team", "Totals"),
    "opponent_totals": ("Opponent_Totals", "Opponent", "Totals"),
}


def fetch_season_page(season: int) -> str:
    response = requests.get(SEASON_URL.format(season=season), headers=HEADERS, timeout=30)
    if response.status_code == 429:
        raise RateLimited(
            "Basketball-Reference rate limit hit (HTTP 429). Wait about an hour before retrying; "
            "the site allows roughly 20 requests per minute."
        )
    response.raise_for_status()
    # Some tables are shipped inside HTML comments and rendered by JavaScript;
    # removing the comment markers exposes them to the HTML parser.
    return re.sub(r"<!--|-->", "", response.text)


def parse_table(html: str, table_id: str, season: int) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(html), attrs={"id": table_id})
    if not tables:
        raise ValueError(f"Table '{table_id}' not found on the page")
    df = tables[0]

    # Drop repeated header rows and the "League Average" footer row if present.
    df = df[df["Team"].notna() & (df["Team"] != "Team")]
    df = df[df["Team"] != "League Average"].copy()

    # A trailing "*" on the team name marks a playoff team.
    df.insert(1, "Playoffs", df["Team"].str.endswith("*"))
    df["Team"] = df["Team"].str.rstrip("*").str.strip()
    df.insert(0, "Season", season)

    df = df.drop(columns=["Rk"], errors="ignore")
    numeric_cols = df.columns.difference(["Season", "Team", "Playoffs"])
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def fetch_team_stats(season: int, fetch_page: Callable[[int], str] | None = None) -> dict[str, pd.DataFrame]:
    """Return {output_stem: DataFrame} for every table in TABLES."""
    html = re.sub(r"<!--|-->", "", (fetch_page or fetch_season_page)(season))
    results = {}
    for table_id, stem in TABLES.items():
        try:
            results[stem] = parse_table(html, table_id, season)
        except ValueError:
            print(f"  ! {table_id} is not available for {season}; skipping")
    return results


def build_all_stats(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Stack every table into one long table tagged with Perspective and Stat_Basis.

    In Tableau, filter or color by these two columns instead of joining four sheets.
    """
    frames = []
    for stem, df in results.items():
        _, perspective, basis = SHEETS[stem]
        tagged = df.copy()
        tagged.insert(1, "Perspective", perspective)
        tagged.insert(2, "Stat_Basis", basis)
        frames.append(tagged)
    return pd.concat(frames, ignore_index=True)


def write_workbook(results: dict[str, pd.DataFrame], path: Path) -> None:
    sheets = {SHEETS[stem][0]: df for stem, df in results.items()}
    sheets["All_Stats"] = build_all_stats(results)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            ws.freeze_panes = "A2"
            for i, col in enumerate(df.columns, start=1):
                width = max(len(str(col)), df[col].astype(str).str.len().max()) + 2
                ws.column_dimensions[get_column_letter(i)].width = min(width, 30)


def pull_team_tables(season: int, out_root: Path | None = None, excel_dir: Path | None = None,
                     excel: bool | None = None, skip_existing: bool = False,
                     fetch_page: Callable[[int], str] | None = None) -> PullReport:
    """Save the four team/opponent tables for ``season`` as CSVs (and the workbook when ``excel``).

    Defaults: out_root = settings.RAW_DIR, excel_dir = settings.TABLEAU_DIR, excel = settings.TEAM_STATS_EXCEL.
    With ``skip_existing`` and all four CSVs on disk, the page is not fetched.
    """
    out_root = Path(out_root or settings.RAW_DIR)
    excel_dir = Path(excel_dir or settings.TABLEAU_DIR)
    excel = settings.TEAM_STATS_EXCEL if excel is None else excel
    report = PullReport()
    paths = {stem: out_root / f"{stem}_{season}.csv" for stem in TABLES.values()}
    if skip_existing and all(path.exists() for path in paths.values()):
        report.skipped.extend(paths.values())
        return report
    try:
        results = fetch_team_stats(season, fetch_page)
    except RateLimited:
        raise
    except Exception as exc:  # reported; the next season still downloads
        report.failed.append((f"bbref_team {season}", f"{type(exc).__name__}: {exc}"))
        return report
    out_root.mkdir(parents=True, exist_ok=True)
    for stem, df in results.items():
        df.to_csv(paths[stem], index=False)
        report.written.append(paths[stem])
        print(f"  saved {len(df):>2} teams -> {paths[stem]}")
    if excel and results:
        excel_dir.mkdir(parents=True, exist_ok=True)
        book = excel_dir / f"team_stats_{season}.xlsx"
        write_workbook(results, book)
        print(f"  saved workbook  -> {book}")
    return report


def pull_seasons(seasons: list[int], skip_existing: bool = False) -> PullReport:
    """pull_team_tables for each season, settings.BBREF_DELAY_SECONDS apart."""
    report = PullReport()
    for i, season in enumerate(seasons):
        if i:
            time.sleep(settings.BBREF_DELAY_SECONDS)
        print(f"Basketball-Reference team tables {season}:")
        report.merge(pull_team_tables(season, skip_existing=skip_existing))
    return report
