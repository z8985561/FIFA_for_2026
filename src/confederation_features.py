from __future__ import annotations

from itertools import combinations_with_replacement

import pandas as pd

from .world_cup_identity import CONFEDERATION_BY_TEAM

CONFEDERATIONS = ("AFC", "CAF", "CONCACAF", "CONMEBOL", "OFC", "UEFA", "UNKNOWN")
HISTORICAL_CONFEDERATION_BY_TEAM = {
    **CONFEDERATION_BY_TEAM,
    "Cameroon": "CAF",
    "Costa Rica": "CONCACAF",
    "Denmark": "UEFA",
    "Iceland": "UEFA",
    "Nigeria": "CAF",
    "Peru": "CONMEBOL",
    "Poland": "UEFA",
    "Russia": "UEFA",
    "Serbia": "UEFA",
    "Wales": "UEFA",
}
CONFEDERATION_PAIRS = tuple(
    f"{left}_vs_{right}"
    for left, right in combinations_with_replacement(CONFEDERATIONS, 2)
)


def team_confederation(team_name: str) -> str:
    return HISTORICAL_CONFEDERATION_BY_TEAM.get(str(team_name), "UNKNOWN")


def confederation_pair(home_confederation: str, away_confederation: str) -> str:
    left, right = sorted((home_confederation, away_confederation))
    return f"{left}_vs_{right}"


def confederation_feature_columns() -> list[str]:
    columns = [
        "same_confederation_int",
        "cross_confederation_int",
        "elo_diff_cross_confed",
    ]
    columns.extend(f"home_confed_{confederation}" for confederation in CONFEDERATIONS)
    columns.extend(f"away_confed_{confederation}" for confederation in CONFEDERATIONS)
    columns.extend(f"confed_pair_{pair}" for pair in CONFEDERATION_PAIRS)
    return columns


def add_confederation_features(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["home_confederation"] = working["home_team"].map(team_confederation)
    working["away_confederation"] = working["away_team"].map(team_confederation)
    working["same_confederation"] = working["home_confederation"].eq(
        working["away_confederation"]
    )
    working["same_confederation_int"] = working["same_confederation"].astype(int)
    working["cross_confederation_int"] = 1 - working["same_confederation_int"]
    working["elo_diff_cross_confed"] = (
        working["elo_diff"].astype(float) * working["cross_confederation_int"]
    )
    working["confederation_pair"] = [
        confederation_pair(home, away)
        for home, away in zip(
            working["home_confederation"],
            working["away_confederation"],
            strict=True,
        )
    ]

    for confederation in CONFEDERATIONS:
        working[f"home_confed_{confederation}"] = (
            working["home_confederation"].eq(confederation).astype(int)
        )
        working[f"away_confed_{confederation}"] = (
            working["away_confederation"].eq(confederation).astype(int)
        )

    for pair in CONFEDERATION_PAIRS:
        working[f"confed_pair_{pair}"] = working["confederation_pair"].eq(pair).astype(int)

    return working
