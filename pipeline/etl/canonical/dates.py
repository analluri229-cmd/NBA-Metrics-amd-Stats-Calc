"""Date and season conventions.

Seasons are labelled by their end year, matching Basketball-Reference:
2026 means the 2025-26 season. A game in October-December belongs to the
following calendar year's season.

Adapters should prefer the season the source states; ``season_from_date`` is
for rows that carry only a date.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

# (month, day) from which a date belongs to the next season. The 2019-20 season was
# suspended for COVID and finished in the Orlando bubble (restart July 30, Finals to
# October 11, 2020); 2020-21 began December 22, 2020.
SEASON_ROLLOVER = (10, 1)
SEASON_ROLLOVER_EXCEPTIONS = {2020: (12, 1)}


def to_date_id(value: object) -> str | None:
    """Return 'YYYY-MM-DD' for a date, datetime or date-prefixed string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return None
    return date(int(match[1]), int(match[2]), int(match[3])).isoformat()


def season_from_date(value: object) -> int | None:
    date_id = to_date_id(value)
    if date_id is None:
        return None
    year, month, day = int(date_id[:4]), int(date_id[5:7]), int(date_id[8:10])
    rollover = SEASON_ROLLOVER_EXCEPTIONS.get(year, SEASON_ROLLOVER)
    return year + 1 if (month, day) >= rollover else year


def season_label(season: int) -> str:
    """2026 -> '2025-26' (the format stats.nba.com expects)."""
    return f"{season - 1}-{str(season)[-2:]}"


def season_from_label(label: str) -> int:
    """'2025-26' -> 2026. Also accepts a plain end year."""
    text = str(label).strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})", text)
    if match:
        return int(match[1]) + 1
    return int(text)


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    first_sunday = first + timedelta(days=(6 - first.weekday()) % 7)
    return first_sunday + timedelta(weeks=n - 1)


def _last_sunday(year: int, month: int) -> date:
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def _eastern_offset_hours(utc_dt: datetime) -> int:
    """US Eastern UTC offset (-4 in daylight time, -5 otherwise).

    Implemented from the US DST rules so it works without a tz database,
    which Windows Python does not ship.
    """
    year = utc_dt.year
    if year >= 2007:
        start, end = _nth_sunday(year, 3, 2), _nth_sunday(year, 11, 1)
    else:
        start, end = _nth_sunday(year, 4, 1), _last_sunday(year, 10)
    # DST starts 02:00 EST (07:00 UTC) and ends 02:00 EDT (06:00 UTC).
    dst_start = datetime(start.year, start.month, start.day, 7, tzinfo=timezone.utc)
    dst_end = datetime(end.year, end.month, end.day, 6, tzinfo=timezone.utc)
    return -4 if dst_start <= utc_dt < dst_end else -5


def eastern_game_date(timestamp: str) -> str | None:
    """Convert a UTC timestamp like '2000-11-01 00:30:00+00:00' to the US Eastern game date."""
    text = str(timestamp).strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.date().isoformat()
    utc_dt = parsed.astimezone(timezone.utc)
    return (utc_dt + timedelta(hours=_eastern_offset_hours(utc_dt))).date().isoformat()
