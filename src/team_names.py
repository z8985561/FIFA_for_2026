from __future__ import annotations

import unicodedata

TEAM_ALIASES = {
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Curacao": "Cura\u00e7ao",
    "Curaao": "Cura\u00e7ao",
    "Cura\u83bdao": "Cura\u00e7ao",
    "Czechia": "Czech Republic",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Trkiye": "Turkey",
    "T\u00fcrkiye": "Turkey",
    "USA": "United States",
}


def normalize_team_name(name: str) -> str:
    cleaned = unicodedata.normalize("NFKC", " ".join(str(name).strip().split()))
    return TEAM_ALIASES.get(cleaned, cleaned)


def ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))
