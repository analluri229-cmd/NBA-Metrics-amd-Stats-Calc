"""Shared filesystem locations for the ETL layer. The folders are set in pipeline/settings.py."""
from __future__ import annotations

from pipeline import settings

PROJECT_ROOT = settings.PROJECT_ROOT
DB_PATH = settings.WAREHOUSE_PATH
RAW_DIR = settings.RAW_DIR
CLEAN_DIR = settings.CLEAN_DIR
