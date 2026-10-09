"""Historical ingestion (Basketball-Reference + legacy sample files) through the adapter registry."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .orchestrator import HISTORICAL_SOURCES, run_ingest
from .paths import DB_PATH, PROJECT_ROOT, RAW_DIR

RAW_HISTORY_DIR = PROJECT_ROOT / "data" / "raw" / "historical"
RAW_LIVE_DIR = PROJECT_ROOT / "data" / "raw" / "nba_stats"


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []


def _totals(summaries: list[dict]) -> dict[str, int]:
    return {
        "rows_inserted": sum(s.get("rows_inserted", 0) for s in summaries),
        "rows_updated": sum(s.get("rows_updated", 0) for s in summaries),
        "rows_skipped": sum(s.get("rows_skipped", 0) for s in summaries),
        "files_failed": sum(s["status"] == "failed" for s in summaries),
    }


def ingest_historical_directory(raw_root: Path = RAW_DIR, db_path: Path | str = DB_PATH) -> dict[str, int]:
    return _totals(run_ingest(db_path, [*HISTORICAL_SOURCES, "legacy_sample"], raw_root=raw_root))


def ingest_live_directory(raw_root: Path = RAW_DIR, db_path: Path | str = DB_PATH) -> dict[str, int]:
    return _totals(run_ingest(db_path, ["nba_stats"], raw_root=raw_root))


if __name__ == "__main__":
    print(ingest_historical_directory())
    print(ingest_live_directory())
