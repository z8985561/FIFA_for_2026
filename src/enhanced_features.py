from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Any

import pandas as pd

from .confederation_features import add_confederation_features, confederation_feature_columns

FORM_WINDOWS = (5, 10)
DEFAULT_REST_DAYS = 30.0
MAX_REST_DAYS = 365.0
DEFAULT_POINTS_PER_MATCH = 1.0

FORM_METRICS = (
    "matches",
    "points_per_match",
    "goal_diff_per_match",
    "goals_for_per_match",
    "goals_against_per_match",
    "win_rate",
    "competitive_share",
)


def enhanced_feature_columns() -> list[str]:
    columns = [
        "elo_diff",
        "expected_home_win",
        "neutral_int",
        "home_rest_days",
        "away_rest_days",
        "rest_days_diff",
        "is_competitive",
        "fifa_rank_diff",
        "squad_size_diff",
        "squad_age_diff",
        "squad_caps_diff",
    ]

    for window in FORM_WINDOWS:
        for metric in FORM_METRICS:
            columns.extend(
                [
                    f"home_{metric}_last_{window}",
                    f"away_{metric}_last_{window}",
                    f"{metric}_diff_last_{window}",
                ]
            )
    columns.extend(confederation_feature_columns())
    return columns


def clean_rest_days(value: Any) -> float:
    if pd.isna(value):
        return DEFAULT_REST_DAYS
    return min(float(value), MAX_REST_DAYS)


def match_points(goals_for: int, goals_against: int) -> int:
    if goals_for > goals_against:
        return 3
    if goals_for == goals_against:
        return 1
    return 0


def make_team_entry(
    *,
    goals_for: int,
    goals_against: int,
    competition_type: str,
) -> dict[str, float]:
    points = match_points(goals_for, goals_against)
    return {
        "points": float(points),
        "goal_diff": float(goals_for - goals_against),
        "goals_for": float(goals_for),
        "goals_against": float(goals_against),
        "win": 1.0 if points == 3 else 0.0,
        "competitive": 0.0 if competition_type == "friendly" else 1.0,
    }


def summarize_entries(entries: Iterable[dict[str, float]]) -> dict[str, float]:
    values = list(entries)
    matches = len(values)
    if matches == 0:
        return {
            "matches": 0.0,
            "points_per_match": DEFAULT_POINTS_PER_MATCH,
            "goal_diff_per_match": 0.0,
            "goals_for_per_match": 0.0,
            "goals_against_per_match": 0.0,
            "win_rate": 0.0,
            "competitive_share": 0.0,
        }

    return {
        "matches": float(matches),
        "points_per_match": sum(item["points"] for item in values) / matches,
        "goal_diff_per_match": sum(item["goal_diff"] for item in values) / matches,
        "goals_for_per_match": sum(item["goals_for"] for item in values) / matches,
        "goals_against_per_match": sum(item["goals_against"] for item in values) / matches,
        "win_rate": sum(item["win"] for item in values) / matches,
        "competitive_share": sum(item["competitive"] for item in values) / matches,
    }


def prefixed_form_summary(
    history: deque[dict[str, float]],
    prefix: str,
) -> dict[str, float]:
    output: dict[str, float] = {}
    history_list = list(history)
    for window in FORM_WINDOWS:
        summary = summarize_entries(history_list[-window:])
        for metric, value in summary.items():
            output[f"{prefix}_{metric}_last_{window}"] = value
    return output


def add_form_differences(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    for window in FORM_WINDOWS:
        for metric in FORM_METRICS:
            working[f"{metric}_diff_last_{window}"] = (
                working[f"home_{metric}_last_{window}"]
                - working[f"away_{metric}_last_{window}"]
            )
    return working


def build_historical_enhanced_features(matches: pd.DataFrame) -> pd.DataFrame:
    working = matches.sort_values(["match_date", "home_team", "away_team"]).reset_index(drop=True)
    histories: defaultdict[str, deque[dict[str, float]]] = defaultdict(
        lambda: deque(maxlen=max(FORM_WINDOWS))
    )
    rows: list[dict[str, Any]] = []

    for row in working.itertuples(index=False):
        home_team = str(row.home_team)
        away_team = str(row.away_team)
        home_rest_days = clean_rest_days(row.home_rest_days)
        away_rest_days = clean_rest_days(row.away_rest_days)

        feature_row = {
            "match_id": row.match_id,
            "match_date": row.match_date,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": row.home_score,
            "away_score": row.away_score,
            "competition_type": row.competition_type,
            "outcome": row.outcome,
            "elo_diff": float(row.elo_diff),
            "expected_home_win": float(row.expected_home_win),
            "neutral_int": int(bool(row.neutral)),
            "home_rest_days": home_rest_days,
            "away_rest_days": away_rest_days,
            "rest_days_diff": home_rest_days - away_rest_days,
            "is_competitive": int(row.competition_type != "friendly"),
        }
        feature_row.update(prefixed_form_summary(histories[home_team], "home"))
        feature_row.update(prefixed_form_summary(histories[away_team], "away"))
        rows.append(feature_row)

        histories[home_team].append(
            make_team_entry(
                goals_for=int(row.home_score),
                goals_against=int(row.away_score),
                competition_type=str(row.competition_type),
            )
        )
        histories[away_team].append(
            make_team_entry(
                goals_for=int(row.away_score),
                goals_against=int(row.home_score),
                competition_type=str(row.competition_type),
            )
        )

    result = add_confederation_features(add_form_differences(pd.DataFrame(rows)))
    for col in ["fifa_rank_diff", "squad_size_diff", "squad_age_diff", "squad_caps_diff"]:
        if col not in result.columns:
            result[col] = 0
    return result


def build_latest_team_form_features(matches: pd.DataFrame) -> pd.DataFrame:
    working = matches.sort_values(["match_date", "home_team", "away_team"]).reset_index(drop=True)
    histories: defaultdict[str, deque[dict[str, float]]] = defaultdict(
        lambda: deque(maxlen=max(FORM_WINDOWS))
    )

    for row in working.itertuples(index=False):
        histories[str(row.home_team)].append(
            make_team_entry(
                goals_for=int(row.home_score),
                goals_against=int(row.away_score),
                competition_type=str(row.competition_type),
            )
        )
        histories[str(row.away_team)].append(
            make_team_entry(
                goals_for=int(row.away_score),
                goals_against=int(row.home_score),
                competition_type=str(row.competition_type),
            )
        )

    rows = []
    for team_name, history in sorted(histories.items()):
        row = {"team_name": team_name}
        for key, value in prefixed_form_summary(history, "team").items():
            row[key.removeprefix("team_")] = value
        rows.append(row)
    return pd.DataFrame(rows)


def add_2026_rest_days(match_features: pd.DataFrame) -> pd.DataFrame:
    working = match_features.sort_values(["date_et", "match_no"]).reset_index(drop=True).copy()
    last_played: dict[str, pd.Timestamp] = {}
    home_rest: list[float] = []
    away_rest: list[float] = []

    for row in working.itertuples(index=False):
        match_date = pd.Timestamp(row.date_et)
        row_home_rest = (
            float((match_date - last_played[str(row.home_team)]).days)
            if str(row.home_team) in last_played
            else DEFAULT_REST_DAYS
        )
        row_away_rest = (
            float((match_date - last_played[str(row.away_team)]).days)
            if str(row.away_team) in last_played
            else DEFAULT_REST_DAYS
        )
        home_rest.append(clean_rest_days(row_home_rest))
        away_rest.append(clean_rest_days(row_away_rest))
        last_played[str(row.home_team)] = match_date
        last_played[str(row.away_team)] = match_date

    working["home_rest_days"] = home_rest
    working["away_rest_days"] = away_rest
    working["rest_days_diff"] = working["home_rest_days"] - working["away_rest_days"]
    return working.sort_values("match_no").reset_index(drop=True)


def build_2026_enhanced_features(
    match_features: pd.DataFrame,
    historical_matches: pd.DataFrame,
) -> pd.DataFrame:
    form = build_latest_team_form_features(historical_matches)
    features = add_2026_rest_days(match_features)

    home_form = form.rename(
        columns={column: f"home_{column}" for column in form.columns if column != "team_name"}
    ).rename(columns={"team_name": "home_team"})
    away_form = form.rename(
        columns={column: f"away_{column}" for column in form.columns if column != "team_name"}
    ).rename(columns={"team_name": "away_team"})

    features = features.merge(home_form, on="home_team", how="left")
    features = features.merge(away_form, on="away_team", how="left")
    features["neutral_int"] = features["neutral"].astype(int)
    features["is_competitive"] = 1

    for window in FORM_WINDOWS:
        default_values = summarize_entries([])
        for metric, default_value in default_values.items():
            features[f"home_{metric}_last_{window}"] = features[
                f"home_{metric}_last_{window}"
            ].fillna(default_value)
            features[f"away_{metric}_last_{window}"] = features[
                f"away_{metric}_last_{window}"
            ].fillna(default_value)

    features["fifa_rank_diff"] = (features.get("away_fifa_rank", 50) - features.get("home_fifa_rank", 50)).fillna(0)
    features["squad_size_diff"] = (features.get("away_squad_size", 23) - features.get("home_squad_size", 23)).fillna(0)
    features["squad_age_diff"] = (features.get("away_squad_average_age", 26) - features.get("home_squad_average_age", 26)).fillna(0)
    features["squad_caps_diff"] = (features.get("away_squad_total_caps", 500) - features.get("home_squad_total_caps", 500)).fillna(0)
    return add_confederation_features(add_form_differences(features))
