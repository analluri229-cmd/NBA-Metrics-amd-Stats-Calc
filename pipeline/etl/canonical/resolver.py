"""Resolve source team and player identifiers to canonical ids.

Players: Basketball-Reference slugs are canonical. Other sources match by
normalized name, disambiguated by team and season. Manual fixes go in
``data/reference/player_xref_overrides.csv`` (source_name, source_key, player_id).
Anything still unmatched gets a fallback id (``nba_<id>`` / ``name_<slug>``) and
a row in ``unresolved_entity`` for review; ``ingest --force`` re-resolves it later.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from ..paths import PROJECT_ROOT
from .players import is_fallback_id, normalize_name
from .teams import resolve_team_id

OVERRIDES_PATH = PROJECT_ROOT / "data" / "reference" / "player_xref_overrides.csv"


class IdResolver:
    def __init__(
        self,
        players: list[tuple[str, str]] = (),
        xref: dict[tuple[str, str], tuple[str, str]] | None = None,
        player_seasons: list[tuple[str, int, str]] = (),
        overrides: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self._by_name: dict[str, set[str]] = defaultdict(set)
        for player_id, name in players:
            self._index(player_id, name)
        self._xref = dict(xref or {})
        # Fallback ids ever assigned per source key. Kept for the whole run so every file that
        # re-resolves the key can clean up the rows it wrote under the old id.
        self._fallbacks = {key: player_id for key, (player_id, method) in self._xref.items() if method == "fallback"}
        self._overrides = dict(overrides or {})
        self._seasons: dict[str, set[tuple[int, str]]] = defaultdict(set)
        self._season_set: set[int] = set()
        for player_id, season, team_id in player_seasons:
            self._seasons[player_id].add((season, team_id))
            self._season_set.add(season)
        self.xref_team: dict[tuple[str, str], dict] = {}
        self.xref_player: dict[tuple[str, str], dict] = {}
        self.unresolved: dict[tuple[str, str, str], dict] = {}
        # fallback id -> canonical id for players that now resolve; the loader drops the stale rows.
        self.remapped: dict[str, str] = {}

    @classmethod
    def from_connection(cls, conn: sqlite3.Connection, overrides_path: Path | None = None) -> IdResolver:
        players = conn.execute("SELECT player_id, player_name FROM dim_player").fetchall()
        xref = {
            (source, key): (player_id, method)
            for source, key, player_id, method in conn.execute(
                "SELECT source_name, source_key, player_id, match_method FROM xref_player"
            )
        }
        seasons = conn.execute(
            """
            SELECT DISTINCT player_id, season, team_id FROM fact_player_season WHERE team_id IS NOT NULL
            UNION
            SELECT DISTINCT player_id, season, team_id FROM fact_player_season_stat WHERE team_id IS NOT NULL
            """
        ).fetchall()
        return cls(players, xref, seasons, load_overrides(overrides_path))

    # --- one resolver per ingest run ------------------------------------------
    # Building the resolver reads the whole warehouse, so an ingest run builds it
    # once and reuses it for every file: begin_file() clears what the previous
    # file recorded, commit_file() remembers its mappings after a successful load.

    def begin_file(self) -> None:
        self.xref_team, self.xref_player, self.unresolved, self.remapped = {}, {}, {}, {}

    def commit_file(self) -> None:
        for (source_name, source_key), row in self.xref_player.items():
            self._xref[(source_name, source_key)] = (row["player_id"], row["match_method"])
            if row["match_method"] == "fallback":
                self._fallbacks[(source_name, source_key)] = row["player_id"]

    def _index(self, player_id: str, name: str) -> None:
        if not is_fallback_id(player_id):
            self._by_name[normalize_name(name)].add(player_id)

    # --- teams --------------------------------------------------------------

    def team(self, source_name: str, raw_value: object, context: dict | None = None) -> str | None:
        raw = str(raw_value or "").strip()
        team_id = resolve_team_id(raw)
        if team_id is not None:
            self.xref_team[(source_name, raw)] = {"source_name": source_name, "source_key": raw, "team_id": team_id}
        elif raw:
            self._unresolved("team", source_name, raw, raw, None, context)
        return team_id

    # --- players ------------------------------------------------------------

    def register_player(self, source_name: str, player_id: str, name: str, season: int | None = None,
                        team_id: str | None = None) -> str:
        """Record a player whose canonical id the source supplies directly (bbref slugs)."""
        self._index(player_id, name)
        if season is not None and team_id:
            self._seasons[player_id].add((season, team_id))
            self._season_set.add(season)
        self._record_player(source_name, player_id, player_id, name, "source_id")
        return player_id

    def known_player(self, source_name: str, source_key: str) -> str | None:
        """The canonical id already mapped to a source key (override or a real match), without recording."""
        key = (source_name, str(source_key))
        if key in self._overrides:
            return self._overrides[key]
        known = self._xref.get(key)
        return known[0] if known and known[1] != "fallback" else None

    def player(self, source_name: str, source_key: str, name: str, team_id: str | None = None,
               season: int | None = None, fallback_id: str | None = None) -> str:
        key = (source_name, str(source_key))
        if key in self._overrides:
            return self._record_player(source_name, source_key, self._overrides[key], name, "override")

        known = self._xref.get(key)
        if known and known[1] != "fallback":
            return self._record_player(source_name, source_key, known[0], name, known[1])

        candidates = self._by_name.get(normalize_name(name), set())
        reason = "ambiguous" if len(candidates) > 1 else "no_match"
        if len(candidates) == 1:
            only = next(iter(candidates))
            # Once a season's canonical players are known, a lone name match must have played that
            # season; otherwise it is a different player with the same name from another era.
            if season is None or season not in self._season_set or self._played(only, season):
                return self._record_player(source_name, source_key, only, name, "name")
            reason = "name_match_not_in_season"
        elif len(candidates) > 1 and season is not None:
            narrowed = {pid for pid in candidates if self._played(pid, season)}
            if len(narrowed) > 1 and team_id:
                narrowed = {pid for pid in narrowed if (season, team_id) in self._seasons[pid]}
            if len(narrowed) == 1:
                return self._record_player(source_name, source_key, next(iter(narrowed)), name, "name_team_season")

        player_id = fallback_id or f"{source_name}_{source_key}"
        self._unresolved("player", source_name, str(source_key), name, player_id,
                         {"reason": reason, "team_id": team_id, "season": season,
                          "candidates": sorted(candidates)})
        return self._record_player(source_name, source_key, player_id, name, "fallback")

    def _played(self, player_id: str, season: int) -> bool:
        return any(s == season for s, _ in self._seasons[player_id])

    def _record_player(self, source_name: str, source_key: str, player_id: str, name: str, method: str) -> str:
        old_id = self._fallbacks.get((source_name, str(source_key)))
        if old_id and old_id != player_id:
            self.remapped[old_id] = player_id
        self.xref_player[(source_name, str(source_key))] = {
            "source_name": source_name, "source_key": str(source_key), "player_id": player_id,
            "player_name": name, "match_method": method,
        }
        return player_id

    def _unresolved(self, entity_type: str, source_name: str, source_key: str, raw_value: str,
                    fallback_id: str | None, context: dict | None) -> None:
        self.unresolved[(entity_type, source_name, source_key)] = {
            "entity_type": entity_type, "source_name": source_name, "source_key": source_key,
            "raw_value": raw_value, "fallback_id": fallback_id,
            "context": json.dumps(context, sort_keys=True) if context else None,
        }


def load_overrides(path: Path | None = None) -> dict[tuple[str, str], str]:
    path = path or OVERRIDES_PATH
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            (row["source_name"].strip(), row["source_key"].strip()): row["player_id"].strip()
            for row in csv.DictReader(handle)
            if row.get("player_id", "").strip()
        }
