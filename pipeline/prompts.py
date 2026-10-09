"""Questions the menu asks, each repeated until the answer is usable. Enter takes the [default].

Every function takes ``ask`` (default: input) and ``say`` (default: print) so tests can script answers.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from pipeline import settings
from pipeline.etl.canonical.dates import season_label

Ask = Callable[[str], str]
Say = Callable[[str], None]


def ask_seasons(default: str, minimum: int = settings.FIRST_NBA_STATS_SEASON,
                ask: Ask = input, say: Say = print) -> list[int]:
    """Season end years, e.g. '2026', '2025-26', '2017-2025' or '2010-2012, 2026'."""
    from pipeline.etl.orchestrator import parse_seasons

    current = settings.current_season()
    while True:
        answer = ask(f"Seasons by end year, 2026 = 2025-26 [{default}]: ").strip() or default
        try:
            seasons = parse_seasons(answer.replace(",", " ").split())
        except ValueError:
            say(f"  Couldn't read {answer!r}. Try 2026 or 2017-2025.")
            continue
        if not seasons or seasons[0] < minimum or seasons[-1] > current:
            say(f"  Seasons must be between {minimum} and {current}.")
            continue
        say(f"  -> {len(seasons)} season(s): {season_label(seasons[0])} to {season_label(seasons[-1])}")
        return seasons


def ask_yes_no(question: str, default: bool, ask: Ask = input, say: Say = print) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = ask(f"{question} {hint}: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        say("  Please answer y or n.")


def ask_choice(question: str, options: dict[str, str], default: str, ask: Ask = input, say: Say = print) -> str:
    """Show numbered ``options`` ({key: description}) and return the chosen key."""
    for key, text in options.items():
        say(f"  {key}) {text}")
    while True:
        answer = ask(f"{question} [{default}]: ").strip().lower() or default
        if answer in options:
            return answer
        say(f"  {answer!r} isn't one of the options: {', '.join(options)}.")


def ask_date(question: str, default: str | None = None, ask: Ask = input, say: Say = print) -> date:
    hint = f" [{default}]" if default else ""
    while True:
        answer = ask(f"{question} (YYYY-MM-DD){hint}: ").strip() or (default or "")
        try:
            return date.fromisoformat(answer)
        except ValueError:
            say(f"  Couldn't read {answer!r}. Use YYYY-MM-DD, e.g. 2025-11-01.")
