"""Fetch raw Basketball-Reference files. Network only; parsing lives in the adapters.

Basketball-Reference allows roughly 20 requests per minute, so every request is
followed by ``settings.BBREF_DELAY_SECONDS``. A full season of player stat pages is 8
requests; ``pull_season`` adds 3 more via ``basketball_reference_web_scraper``.

``fetch_team_stats.py`` (team/opponent tables) is still run on its own.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from pipeline import settings

from ...paths import RAW_DIR
from ..pulling import NotAvailable, PullReport, with_retries
from .player_season import PLAYER_PAGES

OUT_ROOT = RAW_DIR / "basketball_reference"
PAGE_URL = "https://www.basketball-reference.com/leagues/NBA_{season}_{page}.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _season_dir(season: int, out_root: Path) -> Path:
    path = out_root / str(season)
    path.mkdir(parents=True, exist_ok=True)
    return path


class RateLimited(RuntimeError):
    """HTTP 429. Basketball-Reference blocks for about an hour, so the whole pull stops."""


def pull_player_tables(season: int, tables: list[str] | None = None, out_root: Path = OUT_ROOT,
                       delay: float | None = None, skip_existing: bool = False,
                       retries: int = 3) -> PullReport:
    """Save each league player stat page unmodified as player_<table>.html.

    A page that does not exist for the season (404) is reported as unavailable and
    skipped; other errors are retried, then reported; a 429 stops the pull.
    """
    delay = settings.BBREF_DELAY_SECONDS if delay is None else delay
    import requests

    report = PullReport()
    requested = False
    for table in tables or list(PLAYER_PAGES):
        path = out_root / str(season) / f"player_{table}.html"
        if skip_existing and path.exists():
            report.skipped.append(path)
            continue
        if requested:
            time.sleep(delay)
        requested = True
        url = PAGE_URL.format(season=season, page=PLAYER_PAGES[table])

        def fetch() -> bytes:
            response = requests.get(url, headers=HEADERS, timeout=60)
            if response.status_code == 429:
                raise RateLimited("Basketball-Reference rate limit hit (HTTP 429); wait an hour before retrying.")
            if response.status_code == 404:
                raise NotAvailable(url)
            response.raise_for_status()
            return response.content

        try:
            content = with_retries(fetch, retries)
        except RateLimited:
            raise
        except NotAvailable:
            report.unavailable.append(f"{season} {table}")
            print(f"  not available: {url}")
            continue
        except Exception as exc:
            report.failed.append((f"{season} {table}", f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED {url}: {type(exc).__name__}: {exc}")
            continue
        # Write the bytes as served (UTF-8). response.text would decode as ISO-8859-1
        # because the site sends no charset header, mangling names like Jokić.
        _season_dir(season, out_root)
        path.write_bytes(content)
        report.written.append(path)
        print(f"  saved {url} -> {path}")
    return report


def pull_season(season: int, out_root: Path = OUT_ROOT, delay: float | None = None) -> list[Path]:
    """Season totals, schedule and standings through basketball_reference_web_scraper."""
    delay = settings.BBREF_DELAY_SECONDS if delay is None else delay
    from basketball_reference_web_scraper import client
    from basketball_reference_web_scraper.data import OutputType

    season_dir = _season_dir(season, out_root)
    calls = {
        "players_season_totals": client.players_season_totals,
        "season_schedule": client.season_schedule,
        "standings": client.standings,
    }
    written = []
    for i, (name, call) in enumerate(calls.items()):
        if i:
            time.sleep(delay)
        path = season_dir / f"{name}.csv"
        call(season_end_year=season, output_type=OutputType.CSV, output_file_path=str(path))
        written.append(path)
        print(f"  saved {name} -> {path}")
    return written


def pull_box_scores(start: date, end: date | None = None, out_root: Path = OUT_ROOT,
                    delay: float | None = None) -> list[Path]:
    """Daily player box scores for each date in [start, end]."""
    delay = settings.BBREF_DELAY_SECONDS if delay is None else delay
    from basketball_reference_web_scraper import client
    from basketball_reference_web_scraper.data import OutputType

    from ...canonical.dates import season_from_date

    written = []
    day, end = start, end or start
    while day <= end:
        if written:
            time.sleep(delay)
        path = _season_dir(season_from_date(day), out_root) / f"player_box_scores_{day.isoformat()}.csv"
        client.player_box_scores(day=day.day, month=day.month, year=day.year,
                                 output_type=OutputType.CSV, output_file_path=str(path))
        written.append(path)
        print(f"  saved box scores {day} -> {path}")
        day += timedelta(days=1)
    return written
