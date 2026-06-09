from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss

from .data_pipeline import prepare_research_data
from .elo import EloConfig, expected_home_score
from .project_paths import (
    BASELINE_METRICS_PATH,
    BASELINE_PREDICTIONS_PATH,
    FIXTURES_PATH,
    MATCHES_PATH,
    RATINGS_PATH,
)

TARGET_ORDER = ["away_win", "draw", "home_win"]


@dataclass(frozen=True)
class BaselineMetrics:
    train_matches: int
    test_matches: int
    accuracy: float
    log_loss: float
    brier_score: float


def ensure_processed_data() -> None:
    if not MATCHES_PATH.exists() or not RATINGS_PATH.exists() or not FIXTURES_PATH.exists():
        prepare_research_data()


def prepare_feature_frame(matches: pd.DataFrame) -> pd.DataFrame:
    frame = matches.copy()
    frame["neutral_int"] = frame["neutral"].astype(int)
    frame["home_rest_days"] = frame["home_rest_days"].fillna(30.0).clip(upper=365.0)
    frame["away_rest_days"] = frame["away_rest_days"].fillna(30.0).clip(upper=365.0)
    frame["is_competitive"] = (frame["competition_type"] != "friendly").astype(int)
    return frame


def feature_columns() -> list[str]:
    return [
        "elo_diff",
        "expected_home_win",
        "neutral_int",
        "home_rest_days",
        "away_rest_days",
        "is_competitive",
    ]


def chronological_split(
    frame: pd.DataFrame, test_share: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values("match_date").reset_index(drop=True)
    split_index = int(len(ordered) * (1.0 - test_share))
    split_index = max(split_index, 1)
    return ordered.iloc[:split_index].copy(), ordered.iloc[split_index:].copy()


def multiclass_brier_score(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    encoded = np.eye(len(TARGET_ORDER))[y_true]
    return float(np.mean(np.sum((probabilities - encoded) ** 2, axis=1)))


def train_baseline_model(matches: pd.DataFrame) -> tuple[LogisticRegression, BaselineMetrics]:
    prepared = prepare_feature_frame(matches)
    train_frame, test_frame = chronological_split(prepared)

    X_train = train_frame[feature_columns()]
    X_test = test_frame[feature_columns()]
    y_train = train_frame["outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    y_test = test_frame["outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})

    model = LogisticRegression(
        max_iter=1000,
        random_state=7,
    )
    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)
    predictions = model.predict(X_test)
    metrics = BaselineMetrics(
        train_matches=len(train_frame),
        test_matches=len(test_frame),
        accuracy=float(accuracy_score(y_test, predictions)),
        log_loss=float(log_loss(y_test, probabilities, labels=list(range(len(TARGET_ORDER))))),
        brier_score=multiclass_brier_score(y_test.to_numpy(), probabilities),
    )
    return model, metrics


def build_fixture_feature_frame(fixtures: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    config = EloConfig()
    rating_map = ratings.set_index("team_name")["latest_elo"].to_dict()

    known_fixtures = fixtures[
        fixtures["home_team"].ne("TBD") & fixtures["away_team"].ne("TBD")
    ].copy()
    known_fixtures["pre_match_elo_home"] = (
        known_fixtures["home_team"].map(rating_map).fillna(config.initial_rating)
    )
    known_fixtures["pre_match_elo_away"] = (
        known_fixtures["away_team"].map(rating_map).fillna(config.initial_rating)
    )
    known_fixtures["expected_home_win"] = known_fixtures.apply(
        lambda row: expected_home_score(
            float(row["pre_match_elo_home"]),
            float(row["pre_match_elo_away"]),
            neutral=True,
            config=config,
        ),
        axis=1,
    )
    known_fixtures["elo_diff"] = (
        known_fixtures["pre_match_elo_home"] - known_fixtures["pre_match_elo_away"]
    )
    known_fixtures["neutral_int"] = 1
    known_fixtures["home_rest_days"] = 30.0
    known_fixtures["away_rest_days"] = 30.0
    known_fixtures["is_competitive"] = 1
    return known_fixtures


def generate_predictions(
    model: LogisticRegression,
    fixtures: pd.DataFrame,
    ratings: pd.DataFrame,
) -> pd.DataFrame:
    features = build_fixture_feature_frame(fixtures, ratings)
    probabilities = model.predict_proba(features[feature_columns()])
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
                    "time_et",
                    "date_bj",
                    "time_bj",
                    "home_team",
                    "away_team",
                    "venue",
                    "city",
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
    return output


def main() -> None:
    ensure_processed_data()

    matches = pd.read_parquet(MATCHES_PATH)
    ratings = pd.read_parquet(RATINGS_PATH)
    fixtures = pd.read_parquet(FIXTURES_PATH)

    model, metrics = train_baseline_model(matches)
    predictions = generate_predictions(model, fixtures, ratings)

    BASELINE_METRICS_PATH.write_text(
        json.dumps(asdict(metrics), indent=2),
        encoding="utf-8",
    )
    predictions.to_csv(BASELINE_PREDICTIONS_PATH, index=False, encoding="utf-8-sig")

    print(f"metrics_path: {BASELINE_METRICS_PATH}")
    print(f"predictions_path: {BASELINE_PREDICTIONS_PATH}")
    print(json.dumps(asdict(metrics), indent=2))


if __name__ == "__main__":
    main()
