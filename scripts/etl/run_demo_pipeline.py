"""Offline demo: bootstrap, ingest every raw file in data/raw/, build features, export CSVs."""
from __future__ import annotations

from .orchestrator import run_pipeline


def run_demo_pipeline() -> dict[str, object]:
    result = run_pipeline()
    return {k: v for k, v in result.items() if k != "failed"} | {"failed_files": len(result["failed"])}


if __name__ == "__main__":
    print(run_demo_pipeline())
