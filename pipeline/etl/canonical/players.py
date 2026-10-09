"""Player name normalization used to match players across sources."""
from __future__ import annotations

import re
import unicodedata

NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

# IDs minted when a player cannot be matched to a Basketball-Reference slug.
FALLBACK_PREFIXES = ("nba_", "name_")


# Letters that Unicode does not decompose into a base letter + accent.
_SPECIAL_LETTERS = str.maketrans({"ı": "i", "ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D",
                                  "ß": "ss", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "þ": "th"})


def normalize_name(name: object) -> str:
    """'Nikola Jokić' -> 'nikola jokic', 'Jaren Jackson Jr.' -> 'jaren jackson', 'Ömer Aşık' -> 'omer asik'."""
    text = unicodedata.normalize("NFKD", str(name or "").translate(_SPECIAL_LETTERS))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"['.]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [token for token in text.split() if token not in NAME_SUFFIXES]
    return " ".join(tokens)


def name_slug(name: object) -> str:
    return "name_" + normalize_name(name).replace(" ", "_")


def is_fallback_id(player_id: str) -> bool:
    return player_id.startswith(FALLBACK_PREFIXES)
