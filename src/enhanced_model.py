from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .baseline_model import TARGET_ORDER, chronological_split
from .data_pipeline import prepare_research_data
from .enhanced_features import (
    build_2026_enhanced_features,
    build_historical_enhanced_features,
    enhanced_feature_columns,
)
from .feature_store import prepare_match_feature_store
from .market_features import attach_market_features
from .odds_pipeline import prepare_odds_features
from .probability_calibration import (
    DEFAULT_PROBABILITY_FLOOR,
    DEFAULT_TEMPERATURE,
    apply_upset_protection,
)
from .project_paths import (
    ENHANCED_METRICS_PATH,
    ENHANCED_PREDICTIONS_PATH,
    HISTORICAL_MATCH_FEATURE_STORE_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    MATCH_ODDS_FEATURES_PATH,
    MATCHES_PATH,
    RATINGS_PATH,
    ensure_project_directories,
)


@dataclass(frozen=True)
class EnhancedMetrics:
    train_matches: int
    test_matches: int
    accuracy: float
    log_loss: float
    brier_score: float
    feature_count: int
    probability_temperature: float
    probability_floor: float


@dataclass(frozen=True)
class EnhancedOutputs:
    historical_feature_store_path: str
    metrics_path: str
    predictions_path: str
    historical_rows: int
    prediction_rows: int
    metrics: EnhancedMetrics


def ensure_enhanced_inputs() -> None:
    if not MATCHES_PATH.exists() or not RATINGS_PATH.exists():
        prepare_research_data()
    if not MATCH_FEATURE_STORE_2026_PATH.exists():
        prepare_match_feature_store()
    if not MATCH_ODDS_FEATURES_PATH.exists():
        prepare_odds_features()


def multiclass_brier_score(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    encoded = np.eye(len(TARGET_ORDER))[y_true]
    return float(np.mean(np.sum((probabilities - encoded) ** 2, axis=1)))


def prepare_historical_feature_store(matches: pd.DataFrame) -> pd.DataFrame:
    features = build_historical_enhanced_features(matches)
    HISTORICAL_MATCH_FEATURE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(HISTORICAL_MATCH_FEATURE_STORE_PATH, index=False)
    return features


def train_enhanced_model(
    historical_features: pd.DataFrame,
) -> tuple[object, EnhancedMetrics]:
    train_frame, test_frame = chronological_split(historical_features)
    columns = enhanced_feature_columns()

    X_train = train_frame[columns]
    X_test = test_frame[columns]
    y_train = train_frame["outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    y_test = test_frame["outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=17),
    )
    model.fit(X_train, y_train)

    probabilities = apply_upset_protection(model.predict_proba(X_test))
    predictions = probabilities.argmax(axis=1)
    metrics = EnhancedMetrics(
        train_matches=len(train_frame),
        test_matches=len(test_frame),
        accuracy=float(accuracy_score(y_test, predictions)),
        log_loss=float(log_loss(y_test, probabilities, labels=list(range(len(TARGET_ORDER))))),
        brier_score=multiclass_brier_score(y_test.to_numpy(), probabilities),
        feature_count=len(columns),
        probability_temperature=DEFAULT_TEMPERATURE,
        probability_floor=DEFAULT_PROBABILITY_FLOOR,
    )
    return model, metrics


def generate_enhanced_predictions(
    model: object,
    match_features_2026: pd.DataFrame,
    historical_matches: pd.DataFrame,
    match_odds_features: pd.DataFrame,
) -> pd.DataFrame:
    features = build_2026_enhanced_features(match_features_2026, historical_matches)
    feature_frame = features[enhanced_feature_columns()]
    probabilities = apply_upset_protection(model.predict_proba(feature_frame))
    probability_frame = pd.DataFrame(
        probabilities,
        columns=["away_win_probability", "draw_probability", "home_win_probability"],
    )

    output = pd.concat(
        [
            features[
                [
                    "match_no",
                    "stage",
                    "group_name",
                    "date_et",
                    "home_team",
                    "away_team",
                    "home_confederation",
                    "away_confederation",
                    "same_confederation",
                    "confederation_pair",
                    "home_latest_elo",
                    "away_latest_elo",
                    "elo_diff",
                    "expected_home_win",
                    "home_rest_days",
                    "away_rest_days",
                    "rest_days_diff",
                    "points_per_match_diff_last_5",
                    "goal_diff_per_match_diff_last_5",
                    "win_rate_diff_last_10",
                ]
            ].reset_index(drop=True),
            probability_frame.reset_index(drop=True),
        ],
        axis=1,
    )
    output["predicted_outcome"] = output[
        ["away_win_probability", "draw_probability", "home_win_probability"]
    ].idxmax(axis=1)
    output["predicted_outcome"] = output["predicted_outcome"].str.replace(
        "_probability",
        "",
        regex=False,
    )
    output = attach_market_features(
        output,
        match_odds_features,
        prediction_date_column="date_et",
        market_date_timezone="America/New_York",
    )
    return output.sort_values("match_no").reset_index(drop=True)


def prepare_enhanced_outputs() -> EnhancedOutputs:
    ensure_project_directories()
    ensure_enhanced_inputs()

    matches = pd.read_parquet(MATCHES_PATH)
    match_features_2026 = pd.read_parquet(MATCH_FEATURE_STORE_2026_PATH)
    match_odds_features = pd.read_parquet(MATCH_ODDS_FEATURES_PATH)

    historical_features = prepare_historical_feature_store(matches)
    model, metrics = train_enhanced_model(historical_features)
    predictions = generate_enhanced_predictions(
        model,
        match_features_2026,
        matches,
        match_odds_features,
    )

    ENHANCED_METRICS_PATH.write_text(
        json.dumps(asdict(metrics), indent=2),
        encoding="utf-8",
    )
    predictions.to_csv(ENHANCED_PREDICTIONS_PATH, index=False, encoding="utf-8-sig")
    return EnhancedOutputs(
        historical_feature_store_path=str(HISTORICAL_MATCH_FEATURE_STORE_PATH),
        metrics_path=str(ENHANCED_METRICS_PATH),
        predictions_path=str(ENHANCED_PREDICTIONS_PATH),
        historical_rows=len(historical_features),
        prediction_rows=len(predictions),
        metrics=metrics,
    )


def main() -> None:
    outputs = prepare_enhanced_outputs()

    print(f"historical_feature_store_path: {outputs.historical_feature_store_path}")
    print(f"metrics_path: {outputs.metrics_path}")
    print(f"predictions_path: {outputs.predictions_path}")
    print(json.dumps(asdict(outputs.metrics), indent=2))


if __name__ == "__main__":
    main()
