"""Canonical NBA franchises.

team_id is the current NBA abbreviation. Historical names and the codes other
sources use (Basketball-Reference's BRK/CHO/PHO, relocated franchises) are
aliases of the current franchise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Franchise:
    team_id: str
    team_name: str
    city: str
    conference: str
    division: str
    aliases: tuple[str, ...] = ()


FRANCHISES: tuple[Franchise, ...] = (
    Franchise("ATL", "Atlanta Hawks", "Atlanta", "East", "Southeast"),
    Franchise("BOS", "Boston Celtics", "Boston", "East", "Atlantic"),
    Franchise("BKN", "Brooklyn Nets", "Brooklyn", "East", "Atlantic", ("BRK", "NJN", "New Jersey Nets")),
    Franchise("CHA", "Charlotte Hornets", "Charlotte", "East", "Southeast", ("CHO", "CHH", "Charlotte Bobcats")),
    Franchise("CHI", "Chicago Bulls", "Chicago", "East", "Central"),
    Franchise("CLE", "Cleveland Cavaliers", "Cleveland", "East", "Central"),
    Franchise("DAL", "Dallas Mavericks", "Dallas", "West", "Southwest"),
    Franchise("DEN", "Denver Nuggets", "Denver", "West", "Northwest"),
    Franchise("DET", "Detroit Pistons", "Detroit", "East", "Central"),
    Franchise("GSW", "Golden State Warriors", "San Francisco", "West", "Pacific", ("GS", "GOS")),
    Franchise("HOU", "Houston Rockets", "Houston", "West", "Southwest"),
    Franchise("IND", "Indiana Pacers", "Indianapolis", "East", "Central"),
    Franchise("LAC", "Los Angeles Clippers", "Los Angeles", "West", "Pacific",
              ("LA Clippers", "San Diego Clippers", "SDC")),
    Franchise("LAL", "Los Angeles Lakers", "Los Angeles", "West", "Pacific", ("LA Lakers",)),
    Franchise("MEM", "Memphis Grizzlies", "Memphis", "West", "Southwest", ("VAN", "Vancouver Grizzlies")),
    Franchise("MIA", "Miami Heat", "Miami", "East", "Southeast"),
    Franchise("MIL", "Milwaukee Bucks", "Milwaukee", "East", "Central"),
    Franchise("MIN", "Minnesota Timberwolves", "Minneapolis", "West", "Northwest"),
    Franchise("NOP", "New Orleans Pelicans", "New Orleans", "West", "Southwest",
              ("NOH", "NOK", "NO", "New Orleans Hornets", "New Orleans/Oklahoma City Hornets")),
    Franchise("NYK", "New York Knicks", "New York", "East", "Atlantic", ("NY",)),
    Franchise("OKC", "Oklahoma City Thunder", "Oklahoma City", "West", "Northwest",
              ("SEA", "Seattle SuperSonics")),
    Franchise("ORL", "Orlando Magic", "Orlando", "East", "Southeast"),
    Franchise("PHI", "Philadelphia 76ers", "Philadelphia", "East", "Atlantic"),
    Franchise("PHX", "Phoenix Suns", "Phoenix", "West", "Pacific", ("PHO",)),
    Franchise("POR", "Portland Trail Blazers", "Portland", "West", "Northwest"),
    Franchise("SAC", "Sacramento Kings", "Sacramento", "West", "Pacific", ("KCK", "Kansas City Kings")),
    Franchise("SAS", "San Antonio Spurs", "San Antonio", "West", "Southwest", ("SA",)),
    Franchise("TOR", "Toronto Raptors", "Toronto", "East", "Atlantic"),
    Franchise("UTA", "Utah Jazz", "Salt Lake City", "West", "Northwest", ("UTAH",)),
    Franchise("WAS", "Washington Wizards", "Washington", "East", "Southeast", ("WSB", "Washington Bullets")),
)

FRANCHISES_BY_ID = {f.team_id: f for f in FRANCHISES}


def team_key(value: object) -> str:
    """Upper-case, punctuation-free key used for alias lookups."""
    text = re.sub(r"[^A-Za-z0-9]+", " ", str(value or "")).strip()
    return re.sub(r"\s+", " ", text).upper()


def _build_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for franchise in FRANCHISES:
        for alias in (franchise.team_id, franchise.team_name, *franchise.aliases):
            index[team_key(alias)] = franchise.team_id
    return index


_ALIASES = _build_alias_index()


def resolve_team_id(value: object) -> str | None:
    """Map any known team name or abbreviation to the canonical team_id."""
    key = team_key(value).rstrip("*").strip()
    return _ALIASES.get(key) if key else None


def dim_team_row(team_id: str) -> dict[str, object]:
    franchise = FRANCHISES_BY_ID[team_id]
    return {
        "team_id": franchise.team_id,
        "team_name": franchise.team_name,
        "abbreviation": franchise.team_id,
        "city": franchise.city,
        "conference": franchise.conference,
        "division": franchise.division,
    }
