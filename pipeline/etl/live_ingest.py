from __future__ import annotations

import json
from pathlib import Path

from .paths import DB_PATH, PROJECT_ROOT, RAW_DIR

LIVE_DIR = PROJECT_ROOT / "data" / "raw" / "nba_stats"


def ingest_live_json(directory: Path = LIVE_DIR) -> list[dict[str, object]]:
    """Read raw live JSON payloads without loading them (kept for ad hoc inspection)."""
    results: list[dict[str, object]] = []
    if not directory.exists():
        return results

    for file_path in sorted(directory.rglob("*.json")):
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            results.extend(payload)
        elif isinstance(payload, dict):
            results.append(payload)
    return results


def ingest_live(db_path: Path | str = DB_PATH, season: int | None = None, raw_root: Path = RAW_DIR) -> list[dict]:
    """Load stats.nba.com raw files into the warehouse through the nba_stats adapter."""
    from .orchestrator import run_ingest

    return run_ingest(db_path, ["nba_stats"], season, raw_root=raw_root)


if __name__ == "__main__":
    for summary in ingest_live():
        print(summary)
