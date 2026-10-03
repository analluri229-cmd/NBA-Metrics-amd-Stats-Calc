"""Load the sample raw files (data/raw/historical, data/raw/nba_stats) with canonical ids."""
from __future__ import annotations

from pathlib import Path

from .canonical_mapping import apply_canonical_mapping
from .orchestrator import run_ingest
from .paths import DB_PATH, RAW_DIR


def run_sample_backfill(db_path: Path | str = DB_PATH, raw_root: Path = RAW_DIR) -> dict[str, int]:
    mapping_result = apply_canonical_mapping(db_path)
    summaries = run_ingest(db_path, ["legacy_sample"], raw_root=raw_root)
    player_rows = sum(s.get("rows_inserted", 0) + s.get("rows_updated", 0) for s in summaries)
    return {**mapping_result, "player_game_rows": player_rows, "team_game_rows": 0}


if __name__ == "__main__":
    print(run_sample_backfill())
