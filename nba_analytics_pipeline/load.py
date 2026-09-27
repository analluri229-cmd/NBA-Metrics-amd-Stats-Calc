from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import CLEAN_DATA_DIR, TABLEAU_DATA_DIR


def save_dataframe(df: pd.DataFrame, filename: str, folder: Path | None = None) -> Path:
    if df.empty:
        return Path()

    target_dir = folder or CLEAN_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / filename
    df.to_csv(file_path, index=False)
    return file_path


def save_tableau_ready(df: pd.DataFrame, filename: str) -> Path:
    return save_dataframe(df, filename, TABLEAU_DATA_DIR)
