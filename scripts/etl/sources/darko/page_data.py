"""Decode the data endpoint of www.darko.app (a SvelteKit site).

``/__data.json`` returns each page node's data serialized with the ``devalue``
library: one flat array in which every object, array and value is stored once
and referenced by its index. Index 0 is the root.
"""
from __future__ import annotations

import json
import math

# devalue's reserved negative indices.
_SPECIAL = {-1: None, -2: None, -3: math.nan, -4: math.inf, -5: -math.inf, -6: -0.0}


def unflatten(values: list) -> object:
    """Rebuild the value devalue flattened into ``values``."""
    hydrated: dict[int, object] = {}

    def hydrate(index: int) -> object:
        if index in _SPECIAL:
            return _SPECIAL[index]
        if index in hydrated:
            return hydrated[index]
        value = values[index]
        if isinstance(value, list) and value and isinstance(value[0], str):
            kind = value[0]  # typed value: ["Date", "..."], ["Set", i, ...], ...
            if kind == "Date":
                result = value[1]
            elif kind == "Set":
                result = [hydrate(i) for i in value[1:]]
            elif kind == "Map":
                result = {hydrate(value[i]): hydrate(value[i + 1]) for i in range(1, len(value), 2)}
            elif kind == "BigInt":
                result = int(value[1])
            else:
                raise ValueError(f"unsupported devalue type {kind!r}")
        elif isinstance(value, list):
            result = [hydrate(i) for i in value]
        elif isinstance(value, dict):
            result = {key: hydrate(i) for key, i in value.items()}
        else:
            result = value
        hydrated[index] = result
        return result

    return hydrate(0)


def page_data(payload: dict | str | bytes) -> dict:
    """The leaderboard page's data: ``players`` (column-oriented), ``seasons``, ``asOf``."""
    if isinstance(payload, (str, bytes)):
        payload = json.loads(payload)
    nodes = [node for node in payload.get("nodes", []) if node and node.get("type") == "data"]
    if not nodes:
        raise ValueError("no data node in DARKO response")
    return unflatten(nodes[-1]["data"])


def player_rows(data: dict) -> list[dict]:
    """Turn the column-oriented ``players`` block into one dict per player."""
    players = data.get("players") or {}
    keys, columns = players.get("keys", []), players.get("values", [])
    return [dict(zip(keys, row)) for row in zip(*columns)]
