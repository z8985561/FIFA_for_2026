from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .baseline_model import TARGET_ORDER
from .data_pipeline import prepare_research_data
from .enhanced_features import build_historical_enhanced_features, enhanced_feature_columns
from .project_paths import (
    MATCHES_PATH,
    WORLD_CUP_BACKTEST_METRICS_PATH,
    WORLD_CUP_BACKTEST_PREDICTIONS_PATH,
    ensure_project_directories,
)
from .scoreline_model import (
    clip_goal_rates,
    estimate_dixon_coles_rho,
    matrix_summary,
    scoreline_matrix,
)

WORLD_CUP_START_DATES = {
    2018: date(2018, 6, 14),
    2022: date(2022, 11, 20),
}
GROUP_STAGE_MATCHES = 48
DEFAULT_BACKTEST_YEARS = (2018, 2022)


@dataclass(frozen=True)
class BacktestOutputs:
    metrics_path: str
    predictions_path: str
    years: tuple[int, ...]
    prediction_rows: int
    metric_rows: int


def ensure_backtest_inputs() -> None:
    if not MATCHES_PATH.exists():
        prepare_research_data()


def world_cup_finals(matches: pd.DataFrame, year: int) -> pd.DataFrame:
    match_dates = pd.to_datetime(matches["match_date"])
    finals = matches[
        (matches["tournament"] == "FIFA World Cup")
        & (match_dates.dt.year == year)
    ].copy()
    return finals.sort_values(["match_date", "match_id"]).reset_index(drop=True)


def add_world_cup_stage_labels(finals: pd.DataFrame) -> pd.DataFrame:
    working = finals.sort_values(["match_date", "match_id"]).reset_index(drop=True).copy()
    working["world_cup_match_index"] = working.index + 1
    working["backtest_stage"] = np.where(
        working["world_cup_match_index"] <= GROUP_STAGE_MATCHES,
        "group_stage",
        "knockout",
    )
    return working


def fit_outcome_model(train_features: pd.DataFrame) -> object:
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=23),
    )
    y_train = train_features["outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    model.fit(train_features[enhanced_feature_columns()], y_train)
    return model


def fit_scoreline_models(train_features: pd.DataFrame) -> tuple[object, object, float]:
    columns = enhanced_feature_columns()
    home_model = make_pipeline(
        StandardScaler(),
        PoissonRegressor(alpha=0.01, max_iter=1000),
    )
    away_model = make_pipeline(
        StandardScaler(),
        PoissonRegressor(alpha=0.01, max_iter=1000),
    )
    home_model.fit(train_features[columns], train_features["home_score"])
    away_model.fit(train_features[columns], train_features["away_score"])
    rho = estimate_dixon_coles_rho(
        train_features["home_score"].to_numpy(),
        train_features["away_score"].to_numpy(),
        clip_goal_rates(home_model.predict(train_features[columns])),
        clip_goal_rates(away_model.predict(train_features[columns])),
    )
    return home_model, away_model, rho


def brier_score_multiclass(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    encoded = np.eye(len(TARGET_ORDER))[y_true]
    return float(np.mean(np.sum((probabilities - encoded) ** 2, axis=1)))


def brier_score_binary(actual: pd.Series, probabilities: pd.Series) -> float:
    return float(np.mean((probabilities.to_numpy() - actual.astype(float).to_numpy()) ** 2))


def build_backtest_predictions_for_year(matches: pd.DataFrame, year: int) -> pd.DataFrame:
    start_date = WORLD_CUP_START_DATES[year]
    finals = add_world_cup_stage_labels(world_cup_finals(matches, year))
    if finals.empty:
        raise ValueError(f"No FIFA World Cup finals matches found for {year}")

    through_world_cup = matches[pd.to_datetime(matches["match_date"]).dt.date <= finals[
        "match_date"
    ].max()].copy()
    features = build_historical_enhanced_features(through_world_cup)
    train_features = features[pd.to_datetime(features["match_date"]).dt.date < start_date].copy()
    test_features = features[features["match_id"].isin(finals["match_id"])].copy()
    test_features = test_features.merge(
        finals[["match_id", "world_cup_match_index", "backtest_stage"]],
        on="match_id",
        how="left",
    ).sort_values("world_cup_match_index")

    outcome_model = fit_outcome_model(train_features)
    home_goal_model, away_goal_model, rho = fit_scoreline_models(train_features)

    columns = enhanced_feature_columns()
    outcome_probabilities = outcome_model.predict_proba(test_features[columns])
    home_goal_rates = clip_goal_rates(home_goal_model.predict(test_features[columns]))
    away_goal_rates = clip_goal_rates(away_goal_model.predict(test_features[columns]))

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(test_features.itertuples(index=False)):
        matrix = scoreline_matrix(
            float(home_goal_rates[index]),
            float(away_goal_rates[index]),
            rho=rho,
        )
        summary = matrix_summary(matrix)
        actual_scoreline = f"{int(row.home_score)}-{int(row.away_score)}"
        scoreline_probability = matrix.loc[
            matrix["scoreline"] == actual_scoreline,
            "probability",
        ]
        top_scorelines = matrix.sort_values("probability", ascending=False).head(3)
        top_scoreline = top_scorelines.iloc[0]
        top3_scoreline_set = set(top_scorelines["scoreline"])
        actual_index = TARGET_ORDER.index(row.outcome)
        rows.append(
            {
                "world_cup_year": year,
                "match_id": row.match_id,
                "world_cup_match_index": row.world_cup_match_index,
                "backtest_stage": row.backtest_stage,
                "match_date": row.match_date,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "home_score": row.home_score,
                "away_score": row.away_score,
                "actual_outcome": row.outcome,
                "away_win_probability": float(outcome_probabilities[index][0]),
                "draw_probability": float(outcome_probabilities[index][1]),
                "home_win_probability": float(outcome_probabilities[index][2]),
                "predicted_outcome": TARGET_ORDER[int(np.argmax(outcome_probabilities[index]))],
                "actual_outcome_probability": float(outcome_probabilities[index][actual_index]),
                "home_expected_goals": float(home_goal_rates[index]),
                "away_expected_goals": float(away_goal_rates[index]),
                "dixon_coles_rho": rho,
                **summary,
                "actual_scoreline": actual_scoreline,
                "actual_scoreline_probability": float(
                    scoreline_probability.iloc[0] if not scoreline_probability.empty else 1e-12
                ),
                "top_scoreline": top_scoreline["scoreline"],
                "top_scoreline_probability": float(top_scoreline["probability"]),
                "top3_scorelines": "|".join(top_scorelines["scoreline"].astype(str)),
                "top3_scoreline_probabilities": "|".join(
                    f"{probability:.8f}" for probability in top_scorelines["probability"]
                ),
                "actual_scoreline_in_top_1": bool(actual_scoreline == top_scoreline["scoreline"]),
                "actual_scoreline_in_top_3": bool(actual_scoreline in top3_scoreline_set),
                "actual_over_2_5": int(row.home_score + row.away_score >= 3),
                "actual_btts": int(row.home_score > 0 and row.away_score > 0),
            }
        )
    return pd.DataFrame(rows)


def aggregate_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [
        ("all", predictions),
        *list(predictions.groupby("backtest_stage", sort=True)),
    ]
    for stage, frame in groups:
        y_true = frame["actual_outcome"].map(
            {label: idx for idx, label in enumerate(TARGET_ORDER)}
        ).to_numpy()
        probabilities = frame[
            ["away_win_probability", "draw_probability", "home_win_probability"]
        ].to_numpy()
        rows.append(
            {
                "world_cup_year": (
                    "combined"
                    if frame["world_cup_year"].nunique() > 1
                    else int(frame["world_cup_year"].iloc[0])
                ),
                "backtest_stage": stage,
                "matches": len(frame),
                "outcome_accuracy": float(
                    accuracy_score(
                        y_true,
                        frame["predicted_outcome"].map(
                            {label: idx for idx, label in enumerate(TARGET_ORDER)}
                        ),
                    )
                ),
                "outcome_log_loss": float(
                    log_loss(y_true, probabilities, labels=list(range(len(TARGET_ORDER))))
                ),
                "outcome_brier": brier_score_multiclass(y_true, probabilities),
                "home_goal_mae": float(
                    mean_absolute_error(frame["home_score"], frame["home_expected_goals"])
                ),
                "away_goal_mae": float(
                    mean_absolute_error(frame["away_score"], frame["away_expected_goals"])
                ),
                "scoreline_log_loss": float(
                    -np.log(frame["actual_scoreline_probability"].clip(lower=1e-12)).mean()
                ),
                "scoreline_top1_rate": float(frame["actual_scoreline_in_top_1"].mean()),
                "scoreline_top3_rate": float(frame["actual_scoreline_in_top_3"].mean()),
                "over_2_5_brier": brier_score_binary(
                    frame["actual_over_2_5"], frame["over_2_5_probability"]
                ),
                "btts_brier": brier_score_binary(
                    frame["actual_btts"], frame["both_teams_score_probability"]
                ),
            }
        )
    return pd.DataFrame(rows)


def build_backtest_reports(
    matches: pd.DataFrame,
    years: tuple[int, ...] = DEFAULT_BACKTEST_YEARS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames = [
        build_backtest_predictions_for_year(matches, year)
        for year in years
    ]
    predictions = pd.concat(prediction_frames, ignore_index=True)
    metric_frames = [
        aggregate_metrics(frame)
        for _, frame in predictions.groupby("world_cup_year", sort=True)
    ]
    metric_frames.append(aggregate_metrics(predictions))
    return predictions, pd.concat(metric_frames, ignore_index=True)


def prepare_world_cup_backtest(
    *,
    years: tuple[int, ...] = DEFAULT_BACKTEST_YEARS,
) -> BacktestOutputs:
    ensure_project_directories()
    ensure_backtest_inputs()

    matches = pd.read_parquet(MATCHES_PATH)
    predictions, metrics = build_backtest_reports(matches, years=years)
    predictions.to_csv(WORLD_CUP_BACKTEST_PREDICTIONS_PATH, index=False, encoding="utf-8-sig")
    metrics.to_csv(WORLD_CUP_BACKTEST_METRICS_PATH, index=False, encoding="utf-8-sig")
    return BacktestOutputs(
        metrics_path=str(WORLD_CUP_BACKTEST_METRICS_PATH),
        predictions_path=str(WORLD_CUP_BACKTEST_PREDICTIONS_PATH),
        years=years,
        prediction_rows=len(predictions),
        metric_rows=len(metrics),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backtest World Cup finals predictions.")
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_BACKTEST_YEARS))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_world_cup_backtest(years=tuple(args.years))
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
