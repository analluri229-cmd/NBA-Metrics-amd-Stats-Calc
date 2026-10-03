"""Shared helpers for extractors: retries and a report of what a pull did."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


class NotAvailable(Exception):
    """The source has no such table (e.g. a stat that did not exist that season). Not retried."""


@dataclass
class PullReport:
    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)       # already on disk
    unavailable: list[str] = field(default_factory=list)    # source has no such table
    failed: list[tuple[str, str]] = field(default_factory=list)  # (what, error) after all retries

    def merge(self, other: PullReport) -> PullReport:
        self.written += other.written
        self.skipped += other.skipped
        self.unavailable += other.unavailable
        self.failed += other.failed
        return self

    def summary(self) -> str:
        return (f"written={len(self.written)} skipped_existing={len(self.skipped)} "
                f"unavailable={len(self.unavailable)} failed={len(self.failed)}")


def with_retries(fetch: Callable[[], T], retries: int = 3, base_delay: float = 5.0) -> T:
    """Call ``fetch``; on a transient error wait base_delay, 2x, 4x... and try again."""
    for attempt in range(retries):
        try:
            return fetch()
        except NotAvailable:
            raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(base_delay * 2 ** attempt)
    raise AssertionError("unreachable")
