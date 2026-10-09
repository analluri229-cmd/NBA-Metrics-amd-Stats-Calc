from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pipeline.etl.bootstrap import bootstrap
from pipeline.etl.canonical import resolver
from pipeline.etl.warehouse import connect

FIXTURE_RAW = Path(__file__).parent / "fixtures" / "raw"


@pytest.fixture(autouse=True)
def no_real_overrides(tmp_path, monkeypatch):
    """Tests never read the project's data/reference overrides file."""
    monkeypatch.setattr(resolver, "OVERRIDES_PATH", tmp_path / "no_overrides.csv")


@pytest.fixture
def raw_root(tmp_path) -> Path:
    """A private copy of the fixture raw tree, so tests may add or edit files."""
    root = tmp_path / "raw"
    shutil.copytree(FIXTURE_RAW, root)
    return root


@pytest.fixture
def db_path(tmp_path) -> Path:
    path = tmp_path / "warehouse.db"
    bootstrap(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = connect(db_path)
    yield connection
    connection.close()
