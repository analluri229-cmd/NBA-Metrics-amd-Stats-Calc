"""Prompts re-ask on bad answers, take defaults on Enter, and never accept a future season."""
from __future__ import annotations

from datetime import date

from pipeline import prompts, settings


def answers(*xs):
    queue = list(xs)
    return lambda question: queue.pop(0)


class Said(list):
    def __call__(self, text):
        self.append(text)

    def has(self, words):
        return any(words in line for line in self)


def test_ask_seasons_reprompts_then_accepts(monkeypatch):
    monkeypatch.setattr(settings, "current_season", lambda today=None: 2026)
    said = Said()
    assert prompts.ask_seasons("2026", ask=answers("abc", "2017-2019"), say=said) == [2017, 2018, 2019]
    assert said.has("Couldn't read")


def test_ask_seasons_enter_takes_default(monkeypatch):
    monkeypatch.setattr(settings, "current_season", lambda today=None: 2026)
    assert prompts.ask_seasons("2025-26", ask=answers(""), say=Said()) == [2026]


def test_ask_seasons_rejects_future_season(monkeypatch):
    monkeypatch.setattr(settings, "current_season", lambda today=None: 2026)
    said = Said()
    assert prompts.ask_seasons("2026", ask=answers("2027", "2026"), say=said) == [2026]
    assert said.has("between")


def test_ask_seasons_rejects_before_minimum(monkeypatch):
    monkeypatch.setattr(settings, "current_season", lambda today=None: 2026)
    said = Said()
    assert prompts.ask_seasons("2026", ask=answers("1990", "1997"), say=said) == [1997]
    assert said.has("between 1997 and 2026")


def test_ask_yes_no():
    said = Said()
    assert prompts.ask_yes_no("Go?", True, ask=answers("maybe", "Y"), say=said) is True
    assert said.has("Please answer y or n.")
    assert prompts.ask_yes_no("Go?", False, ask=answers(""), say=Said()) is False


def test_ask_choice():
    said = Said()
    choice = prompts.ask_choice("Pick", {"1": "one", "2": "two"}, "1", ask=answers("9", "2"), say=said)
    assert choice == "2" and said.has("9")


def test_ask_date_rejects_bad_format():
    said = Said()
    assert prompts.ask_date("Start", ask=answers("11/01/2025", "2025-11-01"), say=said) == date(2025, 11, 1)
    assert said.has("YYYY-MM-DD")
