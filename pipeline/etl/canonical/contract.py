"""The contract between source adapters and the canonical loader.

Extractors (network) write raw files. Adapters read one raw file and return
canonical rows without touching the database. The loader validates and writes
those rows and records the run in ``source_manifest``.
"""
from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .resolver import IdResolver


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class RawFile:
    path: Path
    source_name: str
    data_type: str
    season: int | None
    sha256: str

    @classmethod
    def from_path(cls, path: Path, source_name: str, data_type: str, season: int | None) -> RawFile:
        return cls(path, source_name, data_type, season, file_sha256(path))


@dataclass
class AdapterResult:
    source_name: str
    source_system: str
    data_type: str
    season: int | None
    source_file: str
    raw_row_count: int = 0
    records: dict[str, list[dict]] = field(default_factory=dict)
    skipped: list[tuple[int, str]] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    xref_team: list[dict] = field(default_factory=list)
    xref_player: list[dict] = field(default_factory=list)
    remapped: dict[str, str] = field(default_factory=dict)

    def add(self, table: str, row: dict) -> None:
        self.records.setdefault(table, []).append(row)

    def skip(self, index: int, reason: str) -> None:
        self.skipped.append((index, reason))


class SourceAdapter(Protocol):
    source_name: str      # adapter id, recorded in source_manifest.source_name
    source_system: str    # source family used for precedence (see schema.SOURCE_PRECEDENCE)

    def discover(self, raw_root: Path) -> list[RawFile]: ...

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult: ...


def new_result(adapter: SourceAdapter, raw: RawFile) -> AdapterResult:
    return AdapterResult(
        source_name=adapter.source_name,
        source_system=adapter.source_system,
        data_type=raw.data_type,
        season=raw.season,
        source_file=str(raw.path),
    )


# --- small parsing helpers shared by adapters ---------------------------------

def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if isinstance(value, float) and math.isnan(value) else float(value)
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "nan", "NaN", "None"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_bool(value: object) -> bool | None:
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return None
