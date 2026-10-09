"""Fetch DARKO daily player metrics (www.darko.app). Network only; parsing lives in the adapter.

DARKO recomputes every player's DPM after each game day. The leaderboard's data
endpoint returns the whole league as of any date back to 1996-97:

    https://www.darko.app/__data.json?asof=YYYY-MM-DD

Each snapshot is one request, saved unmodified as
``data/raw/darko/<season>/dpm_<data date>.json``. The data date is the last game
date the snapshot includes, as the site reports it.

The site's season view (``?season=``) is not used: it is undocumented and does not
match the snapshot of any single date.

Dates come from the stats.nba.com team game logs already on disk
(``data/raw/nba_stats/<season>/team_game_log[_playoffs].json``), so run the
nba_stats pull for a season first.
"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from ...paths import RAW_DIR
from ..pulling import NotAvailable, PullReport, with_retries
from .page_data import page_data, player_rows

OUT_ROOT = RAW_DIR / "darko"
# One maintainer's site: stay well under anything that looks like load.
REQUEST_DELAY_SECONDS = 3
SNAPSHOT_URL = "https://www.darko.app/__data.json?asof={date}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def game_dates(season: int, raw_root: Path = RAW_DIR) -> tuple[list[str], str | None]:
    """(every game date of the season, last regular-season date) from the nba_stats team game logs."""
    from ..nba_stats.adapter import result_table

    season_dir = raw_root / "nba_stats" / str(season)
    dates: dict[str, bool] = {}  # date -> is regular season
    for name, regular in (("team_game_log.json", True), ("team_game_log_playoffs.json", False)):
        path = season_dir / name
        if not path.exists():
            continue
        columns, rows = result_table(json.loads(path.read_text(encoding="utf-8")))
        index = columns.index("game_date")
        for row in rows:
            dates[str(row[index])[:10]] = regular
    if not dates:
        raise FileNotFoundError(
            f"no team game log in {season_dir}; run `pull --source nba_stats --season {season}` first"
        )
    regular = [d for d, is_regular in dates.items() if is_regular]
    return sorted(dates), max(regular) if regular else None


def snapshot_dates(dates: list[str], every_days: int = 7, keep: tuple[str | None, ...] = ()) -> list[str]:
    """Game dates at least ``every_days`` apart, plus the dates in ``keep`` and the last date."""
    chosen: list[str] = []
    for day in sorted(dates):
        if not chosen or (date.fromisoformat(day) - date.fromisoformat(chosen[-1])).days >= every_days:
            chosen.append(day)
    return sorted({*chosen, *(d for d in keep if d), *dates[-1:]})


def pull_dates(dates: list[str], out_root: Path = OUT_ROOT, delay: float = REQUEST_DELAY_SECONDS,
               skip_existing: bool = False, retries: int = 3) -> PullReport:
    """Save the DARKO snapshot for each date as dpm_<data date>.json under its season folder."""
    import requests

    from ...canonical.dates import season_from_date

    report = PullReport()
    requested = False
    for day in dates:
        existing = out_root / str(season_from_date(day)) / f"dpm_{day}.json"
        if skip_existing and existing.exists():
            report.skipped.append(existing)
            continue
        if requested:
            time.sleep(delay)
        requested = True
        url = SNAPSHOT_URL.format(date=day)

        def fetch() -> tuple[bytes, dict]:
            response = requests.get(url, headers=HEADERS, timeout=60)
            if response.status_code == 404:
                raise NotAvailable(url)
            response.raise_for_status()
            data = page_data(response.content)
            if not (data.get("asOf") or {}).get("dataDate") or not player_rows(data):
                raise NotAvailable(url)
            return response.content, data

        try:
            content, data = with_retries(fetch, retries)
        except NotAvailable:
            report.unavailable.append(day)
            print(f"  not available: {url}")
            continue
        except Exception as exc:
            report.failed.append((day, f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED {url}: {type(exc).__name__}: {exc}")
            continue
        data_date = data["asOf"]["dataDate"][:10]
        path = out_root / str(season_from_date(data_date)) / f"dpm_{data_date}.json"
        if data_date != day and path in report.written:
            print(f"  no new data on {day} (latest: {data_date})")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        report.written.append(path)
        note = "" if data_date == day else f" (latest data: {data_date})"
        print(f"  saved {url} -> {path}{note}")
    return report


def pull_season(season: int, every_days: int = 7, raw_root: Path = RAW_DIR, out_root: Path = OUT_ROOT,
                skip_existing: bool = False) -> PullReport:
    """Snapshots every ``every_days`` game days, plus the last regular-season and last playoff dates."""
    dates, last_regular = game_dates(season, raw_root)
    chosen = snapshot_dates(dates, every_days, keep=(last_regular,))
    print(f"  {len(chosen)} snapshot dates from {chosen[0]} to {chosen[-1]}")
    return pull_dates(chosen, out_root, skip_existing=skip_existing)
