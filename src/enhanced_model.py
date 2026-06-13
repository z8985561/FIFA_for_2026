from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

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
    DEFAULT_SHRINKAGE_K,
    apply_confederation_correction,
    apply_upset_protection,
    build_confederation_correction_factors,
)
from .project_paths import (
    ENHANCED_METRICS_PATH,
    ENHANCED_PREDICTIONS_PATH,
    HISTORICAL_MATCH_FEATURE_STORE_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    MATCH_ODDS_FEATURES_PATH,
    MATCHES_PATH,
    RATINGS_PATH,
    SPORTTERY_MATCH_ODDS_FEATURES_PATH,
    ensure_project_directories,
)
from .sporttery_market_odds_pipeline import prepare_sporttery_market_odds
from .team_names import normalize_team_name


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
    if not SPORTTERY_MATCH_ODDS_FEATURES_PATH.exists():
        prepare_sporttery_market_odds()


def market_feature_source_key(
    frame: pd.DataFrame,
    *,
    market_date_timezone: str = "America/New_York",
) -> pd.DataFrame:
    keyed = frame.copy()
    keyed["home_team_key"] = keyed["home_team"].map(normalize_team_name)
    keyed["away_team_key"] = keyed["away_team"].map(normalize_team_name)
    keyed["team_pair_key"] = keyed[["home_team_key", "away_team_key"]].apply(
        lambda row: "|".join(sorted(map(str, row))),
        axis=1,
    )
    keyed["market_match_date"] = (
        pd.to_datetime(keyed["commence_time"], utc=True, errors="coerce")
        .dt.tz_convert(market_date_timezone)
        .dt.date
    )
    return keyed


def combine_match_odds_feature_sources(
    market_odds_features: pd.DataFrame,
    sporttery_match_odds_features: pd.DataFrame,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if not market_odds_features.empty:
        base = market_feature_source_key(market_odds_features)
        base["source_priority"] = 0
        frames.append(base)
    if not sporttery_match_odds_features.empty:
        sporttery = market_feature_source_key(sporttery_match_odds_features)
        sporttery["source_priority"] = 1
        frames.append(sporttery)
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["market_match_date"])
    combined = combined.sort_values(
        [
            "home_team_key",
            "away_team_key",
            "team_pair_key",
            "market_match_date",
            "source_priority",
        ]
    )
    combined = combined.drop_duplicates(
        subset=["team_pair_key", "market_match_date"],
        keep="last",
    )
    return combined.drop(
        columns=[
            "home_team_key",
            "away_team_key",
            "team_pair_key",
            "market_match_date",
            "source_priority",
        ]
    ).reset_index(drop=True)


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
    # Time decay: weight recent matches higher (linear decay over years)
    date_col = "date_et" if "date_et" in train_frame.columns else "match_date"
    train_dates = pd.to_datetime(train_frame[date_col], errors="coerce")
    latest = train_dates.max()
    age_years = (latest - train_dates).dt.days.clip(lower=0) / 365.25
    weights = 1.0 - 0.3 * np.clip(age_years / 20.0, 0.0, 1.0)  # min weight 0.7 for 20yr old
    model.fit(X_train, y_train, logisticregression__sample_weight=weights)

    raw_probs = model.predict_proba(X_test)
    probabilities = apply_upset_protection(raw_probs)
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
    raw_probs = model.predict_proba(feature_frame)

    # Apply World Cup-specific confederation corrections
    import pickle
    wc_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "world_cup_confederation_corrections.pkl"
    if wc_path.exists():
        with open(wc_path, "rb") as f:
            wc_corrections = pickle.load(f)
        corrected_probs = apply_confederation_correction(
            raw_probs, features["confederation_pair"], wc_corrections,
        )
    else:
        corrected_probs = raw_probs
    probabilities = apply_upset_protection(corrected_probs)
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
    match_odds_features = combine_match_odds_feature_sources(
        pd.read_parquet(MATCH_ODDS_FEATURES_PATH),
        pd.read_parquet(SPORTTERY_MATCH_ODDS_FEATURES_PATH),
    )

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
