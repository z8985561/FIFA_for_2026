from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

from .baseline_model import TARGET_ORDER
from .team_names import normalize_team_name

MODEL_PROBABILITY_COLUMNS = [
    "away_win_probability",
    "draw_probability",
    "home_win_probability",
]
MARKET_PROBABILITY_COLUMNS = [
    "consensus_away_win_probability",
    "consensus_draw_probability",
    "consensus_home_win_probability",
]
BLENDED_PROBABILITY_COLUMNS = [
    "blended_away_win_probability",
    "blended_draw_probability",
    "blended_home_win_probability",
]
MARKET_ODDS_COLUMNS = [
    "home_team",
    "away_team",
    "commence_time",
    "consensus_home_win_probability",
    "consensus_draw_probability",
    "consensus_away_win_probability",
    "avg_market_overround",
    "min_market_overround",
    "max_market_overround",
    "bookmaker_count",
    "latest_bookmaker_update",
    "latest_market_update",
    "latest_fetched_at",
    "market_entropy",
    "favorite_probability",
    "favorite_outcome",
]
OPTIONAL_MARKET_COLUMNS = [
    "avg_market_overround",
    "min_market_overround",
    "max_market_overround",
    "bookmaker_count",
    "latest_bookmaker_update",
    "latest_market_update",
    "latest_fetched_at",
    "market_entropy",
    "favorite_probability",
    "favorite_outcome",
]


def empty_market_feature_columns(predictions: pd.DataFrame) -> pd.DataFrame:
    attached = predictions.copy()
    for column in MARKET_PROBABILITY_COLUMNS + OPTIONAL_MARKET_COLUMNS:
        if column not in attached.columns:
            attached[column] = np.nan
    attached["has_market_odds"] = False
    for source, blended_column in zip(
        MODEL_PROBABILITY_COLUMNS,
        BLENDED_PROBABILITY_COLUMNS,
        strict=True,
    ):
        attached[blended_column] = attached[source]
    attached["model_market_home_gap"] = np.nan
    attached["model_market_draw_gap"] = np.nan
    attached["model_market_away_gap"] = np.nan
    attached["blended_predicted_outcome"] = attached["predicted_outcome"]
    return attached


def blend_model_and_market_probabilities(
    model_probabilities: pd.DataFrame,
    market_features: pd.DataFrame,
    *,
    model_weight: float = 0.65,
) -> pd.DataFrame:
    model_probability_frame = model_probabilities.reset_index(drop=True).copy()
    market_probability_frame = (
        market_features[MARKET_PROBABILITY_COLUMNS]
        .reset_index(drop=True)
        .rename(
            columns={
                "consensus_away_win_probability": "away_win_probability",
                "consensus_draw_probability": "draw_probability",
                "consensus_home_win_probability": "home_win_probability",
            }
        )
    )
    blended = (
        model_weight * model_probability_frame
        + (1.0 - model_weight) * market_probability_frame
    )
    blended = blended.div(blended.sum(axis=1), axis=0)
    return blended.rename(
        columns={
            "away_win_probability": "blended_away_win_probability",
            "draw_probability": "blended_draw_probability",
            "home_win_probability": "blended_home_win_probability",
        }
    )


def normalize_market_feature_frame(
    match_odds_features: pd.DataFrame,
    *,
    market_date_timezone: str,
) -> pd.DataFrame:
    if match_odds_features.empty:
        return pd.DataFrame()

    missing = [
        column
        for column in MARKET_PROBABILITY_COLUMNS + ["home_team", "away_team", "commence_time"]
        if column not in match_odds_features.columns
    ]
    if missing:
        raise ValueError(f"match_odds_features is missing required columns: {missing}")

    market = match_odds_features.copy()
    for column in OPTIONAL_MARKET_COLUMNS:
        if column not in market.columns:
            market[column] = np.nan
    market["home_team"] = market["home_team"].map(normalize_team_name)
    market["away_team"] = market["away_team"].map(normalize_team_name)
    market["market_match_date"] = (
        pd.to_datetime(market["commence_time"], utc=True, errors="coerce")
        .dt.tz_convert(market_date_timezone)
        .dt.date
    )
    normalized = market[MARKET_ODDS_COLUMNS + ["market_match_date"]].dropna(
        subset=["market_match_date"]
    )
    reversed_market = normalized.copy()
    reversed_market[["home_team", "away_team"]] = reversed_market[
        ["away_team", "home_team"]
    ].to_numpy()
    reversed_market[
        ["consensus_home_win_probability", "consensus_away_win_probability"]
    ] = reversed_market[
        ["consensus_away_win_probability", "consensus_home_win_probability"]
    ].to_numpy()
    reversed_market["favorite_outcome"] = reversed_market["favorite_outcome"].replace(
        {"home_win": "away_win", "away_win": "home_win"}
    )
    return pd.concat([normalized, reversed_market], ignore_index=True)


def attach_market_features(
    predictions: pd.DataFrame,
    match_odds_features: pd.DataFrame,
    *,
    prediction_date_column: str = "date_et",
    market_date_timezone: str = "America/New_York",
    model_weight: float = 0.65,
) -> pd.DataFrame:
    if match_odds_features.empty:
        return empty_market_feature_columns(predictions)

    market = normalize_market_feature_frame(
        match_odds_features,
        market_date_timezone=market_date_timezone,
    )
    if market.empty:
        return empty_market_feature_columns(predictions)

    working = predictions.copy()
    working["home_team"] = working["home_team"].map(normalize_team_name)
    working["away_team"] = working["away_team"].map(normalize_team_name)
    working["market_match_date"] = pd.to_datetime(
        working[prediction_date_column],
        errors="coerce",
    ).dt.date

    merged = working.merge(
        market.drop(columns=["commence_time"]),
        on=["home_team", "away_team", "market_match_date"],
        how="left",
    ).drop(columns=["market_match_date"])
    merged["has_market_odds"] = merged["consensus_home_win_probability"].notna()

    market_ready = merged["has_market_odds"]
    for blended_column in BLENDED_PROBABILITY_COLUMNS:
        merged[blended_column] = np.nan
    if market_ready.any():
        blended = blend_model_and_market_probabilities(
            merged.loc[market_ready, MODEL_PROBABILITY_COLUMNS].reset_index(drop=True),
            merged.loc[market_ready],
            model_weight=model_weight,
        )
        for column in blended.columns:
            merged.loc[market_ready, column] = blended[column].to_numpy()

    fallback_pairs = zip(
        MODEL_PROBABILITY_COLUMNS,
        BLENDED_PROBABILITY_COLUMNS,
        strict=True,
    )
    for model_column, blended_column in fallback_pairs:
        merged.loc[~market_ready, blended_column] = merged.loc[~market_ready, model_column]

    merged["model_market_home_gap"] = (
        merged["home_win_probability"] - merged["consensus_home_win_probability"]
    )
    merged["model_market_draw_gap"] = (
        merged["draw_probability"] - merged["consensus_draw_probability"]
    )
    merged["model_market_away_gap"] = (
        merged["away_win_probability"] - merged["consensus_away_win_probability"]
    )
    merged["blended_predicted_outcome"] = (
        merged[BLENDED_PROBABILITY_COLUMNS]
        .idxmax(axis=1)
        .str.replace("blended_", "", regex=False)
        .str.replace("_probability", "", regex=False)
    )
    return merged


def multiclass_brier_score(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    encoded = np.eye(len(TARGET_ORDER))[y_true]
    return float(np.mean(np.sum((probabilities - encoded) ** 2, axis=1)))


def market_metric_summary(
    frame: pd.DataFrame,
    *,
    probability_columns: list[str],
    predicted_outcome_column: str,
    prefix: str,
) -> dict[str, Any]:
    y_true = frame["actual_outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    y_pred = frame[predicted_outcome_column].map(
        {label: idx for idx, label in enumerate(TARGET_ORDER)}
    )
    probabilities = frame[probability_columns].astype(float).to_numpy()
    return {
        f"{prefix}_accuracy": float(accuracy_score(y_true, y_pred)),
        f"{prefix}_log_loss": float(
            log_loss(y_true, probabilities, labels=list(range(len(TARGET_ORDER))))
        ),
        f"{prefix}_brier": multiclass_brier_score(y_true.to_numpy(), probabilities),
    }


def add_market_metric_columns(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    if "has_market_odds" not in working.columns:
        working = empty_market_feature_columns(working)

    if "market_predicted_outcome" not in working.columns:
        working["market_predicted_outcome"] = pd.Series(
            [np.nan] * len(working),
            index=working.index,
            dtype="object",
        )
        market_ready = working["has_market_odds"]
        if market_ready.any():
            working.loc[market_ready, "market_predicted_outcome"] = (
                working.loc[market_ready, MARKET_PROBABILITY_COLUMNS]
                .idxmax(axis=1)
                .str.replace("consensus_", "", regex=False)
                .str.replace("_probability", "", regex=False)
            )

    if "blended_predicted_outcome" not in working.columns:
        working["blended_predicted_outcome"] = (
            working[BLENDED_PROBABILITY_COLUMNS]
            .idxmax(axis=1)
            .str.replace("blended_", "", regex=False)
            .str.replace("_probability", "", regex=False)
        )

    return working
