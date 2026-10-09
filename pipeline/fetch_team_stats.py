"""Download team and opponent stat tables from a Basketball-Reference season page.

Pulls these tables from https://www.basketball-reference.com/leagues/NBA_<year>.html:

    per_poss-team      Team per 100 possessions
    per_poss-opponent  Opponent per 100 possessions (what each team allowed)
    totals-team        Team season totals
    totals-opponent    Opponent season totals (what each team allowed)

Each table is saved as a CSV in data/raw/, and all four are written to one
Excel workbook in data/tableau/ (one sheet per table, plus an "All_Stats" sheet
that stacks them for Tableau).

Usage:
    python fetch_team_stats.py                        # 2025-26 season
    python fetch_team_stats.py --season 2025          # 2024-25 season
    python fetch_team_stats.py --season 2024 2025 2026  # several seasons
    python fetch_team_stats.py --no-excel             # CSVs only
"""
from __future__ import annotations

import argparse
import io
import re
import time
from pathlib import Path

import pandas as pd
import requests
from openpyxl.utils import get_column_letter

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = WORKSPACE_ROOT / "data" / "raw"
DEFAULT_EXCEL_DIR = WORKSPACE_ROOT / "data" / "tableau"
REQUEST_DELAY_SECONDS = 4  # stays under Basketball-Reference's ~20 requests/minute limit
DEFAULT_SEASON = 2026  # Basketball-Reference labels seasons by end year: 2026 = 2025-26

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
        raise RuntimeError(
            "Basketball-Reference rate limit hit (HTTP 429). Wait a while before retrying; "
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


def fetch_team_stats(season: int = DEFAULT_SEASON) -> dict[str, pd.DataFrame]:
    """Return {output_stem: DataFrame} for every table in TABLES."""
    html = fetch_season_page(season)
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", type=int, nargs="+", default=[DEFAULT_SEASON],
                        help="One or more season end years (2026 = 2025-26). Default: %(default)s")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR,
                        help="CSV output folder. Default: data/raw")
    parser.add_argument("--excel-out", type=Path, default=DEFAULT_EXCEL_DIR,
                        help="Excel workbook folder. Default: data/tableau")
    parser.add_argument("--no-excel", action="store_true", help="Skip the Excel workbook")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.excel_out.mkdir(parents=True, exist_ok=True)

    for i, season in enumerate(args.season):
        if i:
            time.sleep(REQUEST_DELAY_SECONDS)
        print(f"Fetching {SEASON_URL.format(season=season)}")
        results = fetch_team_stats(season)

        for stem, df in results.items():
            path = args.out / f"{stem}_{season}.csv"
            df.to_csv(path, index=False)
            print(f"  saved {len(df):>2} teams -> {path}")

        if not args.no_excel and results:
            path = args.excel_out / f"team_stats_{season}.xlsx"
            write_workbook(results, path)
            print(f"  saved workbook  -> {path}")


if __name__ == "__main__":
    main()
