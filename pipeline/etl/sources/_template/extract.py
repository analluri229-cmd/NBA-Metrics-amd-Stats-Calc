"""Download raw files for <your source>. Network only: save responses unmodified, parse nothing.

Copy this folder to pipeline/etl/sources/<your_source>/ and work through each FILL IN.
Real examples: darko/extract.py (one request per date), basketball_reference/team_extract.py
(one page per season), nba_stats/extract.py (many tables per season).
"""
from __future__ import annotations

import time
from pathlib import Path

from pipeline import settings

from ...paths import RAW_DIR
from ..pulling import NotAvailable, PullReport, with_retries  # noqa: F401  (you will use these)

# FILL IN: the folder for this source's raw files, data/raw/<your_source>/<season>/...
OUT_ROOT = RAW_DIR / "template"

# FILL IN: the URL (or API call) for one request. Keep {season} / {date} placeholders.
URL = "https://example.com/stats?season={season}"


def raw_path(season: int, out_root: Path = OUT_ROOT) -> Path:
    # FILL IN: one file per request, named so discover() in adapter.py can find it and read its season.
    return out_root / str(season) / "table.json"


def pull_season(season: int, out_root: Path | None = None, delay: float | None = None,
                skip_existing: bool = False) -> PullReport:
    """Save every raw file for ``season``; report what was written, skipped or failed."""
    out_root = Path(out_root or OUT_ROOT)
    # FILL IN: add <YOUR_SOURCE>_DELAY_SECONDS to pipeline/settings.py and use it here.
    delay = 3 if delay is None else delay
    report = PullReport()
    path = raw_path(season, out_root)
    if skip_existing and path.exists():
        report.skipped.append(path)
        return report
    # FILL IN: fetch with with_retries(...) (see darko/extract.py pull_dates), raise NotAvailable for a
    # missing table, write the response unmodified with path.write_text(...), then report.written.append(path).
    # Sleep `delay` seconds between requests: time.sleep(delay).
    _ = (time, settings, URL, delay)
    raise NotImplementedError("FILL IN: download and save the raw response in pull_season")
