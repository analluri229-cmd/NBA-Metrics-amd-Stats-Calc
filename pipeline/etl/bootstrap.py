from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.etl.canonical_mapping import apply_canonical_mapping
from pipeline.etl.feature_store import initialize_feature_store
from pipeline.etl.warehouse import DB_PATH


def bootstrap(db_path: Path | str = DB_PATH, reset: bool = False) -> dict[str, str]:
    """Create (or with ``reset``, recreate) the warehouse and seed the 30 teams."""
    db_path = Path(db_path)
    if reset and db_path.exists():
        db_path.unlink()
    apply_canonical_mapping(db_path)
    initialize_feature_store(db_path).close()
    return {"warehouse": str(db_path), "feature_store": str(db_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the SQLite warehouse and feature store.")
    parser.add_argument("--reset", action="store_true", help="Delete the existing warehouse first.")
    print(bootstrap(reset=parser.parse_args().reset))
