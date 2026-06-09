from __future__ import annotations

import unicodedata

TEAM_ALIASES = {
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Curacao": "Curaçao",
}


def normalize_team_name(name: str) -> str:
    cleaned = " ".join(str(name).strip().split())
    cleaned = TEAM_ALIASES.get(cleaned, cleaned)
    return cleaned


def ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))
