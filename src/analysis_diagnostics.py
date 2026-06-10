from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

from .baseline_model import TARGET_ORDER
from .project_paths import (
    WORLD_CUP_BACKTEST_CALIBRATION_PATH,
    WORLD_CUP_BACKTEST_CONFEDERATION_PATH,
    WORLD_CUP_BACKTEST_LOW_SCORE_PATH,
    WORLD_CUP_BACKTEST_PREDICTIONS_PATH,
    WORLD_CUP_BACKTEST_UPSET_PATH,
    ensure_project_directories,
)
from .world_cup_backtest import prepare_world_cup_backtest
from .world_cup_identity import CONFEDERATION_BY_TEAM

PROBABILITY_COLUMNS = [
    "away_win_probability",
    "draw_probability",
    "home_win_probability",
]
PROBABILITY_BY_OUTCOME = dict(zip(TARGET_ORDER, PROBABILITY_COLUMNS, strict=True))
CALIBRATION_BINS = np.linspace(0.0, 1.0, 6)
LOW_SCORE_DRAWS = ("0-0", "1-1")

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


@dataclass(frozen=True)
class DiagnosticOutputs:
    calibration_path: str
    confederation_path: str
    low_score_path: str
    upset_path: str
    calibration_rows: int
    confederation_rows: int
    low_score_rows: int
    upset_rows: int


def ensure_diagnostic_inputs(years: tuple[int, ...]) -> None:
    if not WORLD_CUP_BACKTEST_PREDICTIONS_PATH.exists():
        prepare_world_cup_backtest(years=years)


def outcome_probability_frame(predictions: pd.DataFrame) -> pd.DataFrame:
    return predictions[PROBABILITY_COLUMNS].astype(float)


def add_prediction_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    working = predictions.copy()
    probabilities = outcome_probability_frame(working).to_numpy()
    top_indices = probabilities.argmax(axis=1)
    working["top_probability"] = probabilities[np.arange(len(working)), top_indices]
    working["is_correct_prediction"] = working["predicted_outcome"].eq(working["actual_outcome"])
    working["row_log_loss"] = -np.log(
        working["actual_outcome_probability"].astype(float).clip(lower=1e-12)
    )
    working["confidence_bucket"] = pd.cut(
        working["top_probability"],
        bins=CALIBRATION_BINS,
        include_lowest=True,
        right=True,
    ).astype(str)
    return working


def add_confederation_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    working = add_prediction_diagnostics(predictions)
    working["home_confederation"] = working["home_team"].map(HISTORICAL_CONFEDERATION_BY_TEAM)
    working["away_confederation"] = working["away_team"].map(HISTORICAL_CONFEDERATION_BY_TEAM)
    working["home_confederation"] = working["home_confederation"].fillna("UNKNOWN")
    working["away_confederation"] = working["away_confederation"].fillna("UNKNOWN")
    working["same_confederation"] = working["home_confederation"].eq(working["away_confederation"])
    working["confederation_pair"] = [
        "_vs_".join(sorted((home, away)))
        for home, away in zip(
            working["home_confederation"],
            working["away_confederation"],
            strict=True,
        )
    ]
    working["favorite_confederation"] = np.select(
        [
            working["predicted_outcome"].eq("home_win"),
            working["predicted_outcome"].eq("away_win"),
        ],
        [working["home_confederation"], working["away_confederation"]],
        default="DRAW",
    )
    working["underdog_confederation"] = np.select(
        [
            working["predicted_outcome"].eq("home_win"),
            working["predicted_outcome"].eq("away_win"),
        ],
        [working["away_confederation"], working["home_confederation"]],
        default="DRAW",
    )
    working["favorite_matchup_profile"] = (
        working["favorite_confederation"] + "_favorite_vs_" + working["underdog_confederation"]
    )
    working["is_high_confidence_miss"] = (
        working["top_probability"].ge(0.60) & ~working["is_correct_prediction"]
    )
    return working


def year_stage_slices(predictions: pd.DataFrame) -> list[tuple[str | int, str, pd.DataFrame]]:
    slices: list[tuple[str | int, str, pd.DataFrame]] = [("combined", "all", predictions)]
    slices.extend(
        ("combined", stage, frame)
        for stage, frame in predictions.groupby("backtest_stage", sort=True)
    )
    for year, year_frame in predictions.groupby("world_cup_year", sort=True):
        slices.append((int(year), "all", year_frame))
        slices.extend(
            (int(year), stage, frame)
            for stage, frame in year_frame.groupby("backtest_stage", sort=True)
        )
    return slices


def multiclass_brier(frame: pd.DataFrame) -> float:
    y_true = frame["actual_outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    encoded = np.eye(len(TARGET_ORDER))[y_true.to_numpy()]
    squared_errors = (outcome_probability_frame(frame).to_numpy() - encoded) ** 2
    return float(np.mean(np.sum(squared_errors, axis=1)))


def grouped_outcome_metrics(frame: pd.DataFrame) -> dict[str, float]:
    y_true = frame["actual_outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    y_pred = frame["predicted_outcome"].map({label: idx for idx, label in enumerate(TARGET_ORDER)})
    probabilities = outcome_probability_frame(frame).to_numpy()
    return {
        "outcome_accuracy": float(accuracy_score(y_true, y_pred)),
        "outcome_log_loss": float(log_loss(y_true, probabilities, labels=list(range(3)))),
        "outcome_brier": multiclass_brier(frame),
        "avg_top_probability": float(frame["top_probability"].mean()),
        "avg_actual_outcome_probability": float(frame["actual_outcome_probability"].mean()),
        "upset_rate": float((~frame["is_correct_prediction"]).mean()),
        "high_confidence_miss_rate": float(frame["is_high_confidence_miss"].mean()),
    }


def build_calibration_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    working = add_prediction_diagnostics(predictions)
    rows: list[dict[str, Any]] = []
    for year, stage, frame in year_stage_slices(working):
        for interval, bucket in frame.groupby("confidence_bucket", sort=True, observed=False):
            if bucket.empty:
                continue
            rows.append(
                {
                    "world_cup_year": year,
                    "backtest_stage": stage,
                    "calibration_type": "top_class_confidence",
                    "confidence_bucket": interval,
                    "matches": len(bucket),
                    "mean_confidence": float(bucket["top_probability"].mean()),
                    "empirical_accuracy": float(bucket["is_correct_prediction"].mean()),
                    "calibration_gap": float(
                        bucket["is_correct_prediction"].mean() - bucket["top_probability"].mean()
                    ),
                    "avg_actual_outcome_probability": float(
                        bucket["actual_outcome_probability"].mean()
                    ),
                    "avg_row_log_loss": float(bucket["row_log_loss"].mean()),
                }
            )
    return pd.DataFrame(rows)


def build_confederation_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    working = add_confederation_diagnostics(predictions)
    rows: list[dict[str, Any]] = []
    dimensions = [
        "same_confederation",
        "confederation_pair",
        "favorite_matchup_profile",
    ]
    for year, stage, frame in year_stage_slices(working):
        for dimension in dimensions:
            for value, group in frame.groupby(dimension, sort=True):
                if group.empty:
                    continue
                rows.append(
                    {
                        "world_cup_year": year,
                        "backtest_stage": stage,
                        "diagnostic_dimension": dimension,
                        "diagnostic_value": str(value),
                        "matches": len(group),
                        **grouped_outcome_metrics(group),
                    }
                )
    return pd.DataFrame(rows)


def top3_contains(value: object, scoreline: str) -> bool:
    if pd.isna(value):
        return False
    return scoreline in str(value).split("|")


def build_low_score_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    working = add_prediction_diagnostics(predictions)
    knockout = working.loc[working["backtest_stage"].eq("knockout")].copy()
    rows: list[dict[str, Any]] = []
    slices: list[tuple[str | int, pd.DataFrame]] = [("combined", knockout)]
    slices.extend(
        (int(year), frame)
        for year, frame in knockout.groupby("world_cup_year", sort=True)
    )

    for year, frame in slices:
        if frame.empty:
            continue
        for scoreline in LOW_SCORE_DRAWS:
            actual_rows = frame.loc[frame["actual_scoreline"].eq(scoreline)]
            top3_scoreline_hits = frame["top3_scorelines"].map(
                lambda value, expected=scoreline: top3_contains(value, expected)
            )
            rows.append(
                {
                    "world_cup_year": year,
                    "backtest_stage": "knockout",
                    "diagnostic_value": scoreline,
                    "knockout_matches": len(frame),
                    "actual_matches": len(actual_rows),
                    "top3_inclusion_matches": int(top3_scoreline_hits.sum()),
                    "top3_inclusion_rate": float(top3_scoreline_hits.mean()),
                    "actual_top3_hits": int(actual_rows["actual_scoreline_in_top_3"].sum()),
                    "actual_top3_hit_rate": float(
                        actual_rows["actual_scoreline_in_top_3"].mean()
                        if not actual_rows.empty
                        else 0.0
                    ),
                    "avg_actual_scoreline_probability": float(
                        actual_rows["actual_scoreline_probability"].mean()
                        if not actual_rows.empty
                        else 0.0
                    ),
                }
            )

        low_draw_rows = frame.loc[frame["actual_scoreline"].isin(LOW_SCORE_DRAWS)]
        top3_low_draw_hits = frame["top3_scorelines"].map(
            lambda value: any(
                top3_contains(value, scoreline)
                for scoreline in LOW_SCORE_DRAWS
            )
        )
        rows.append(
            {
                "world_cup_year": year,
                "backtest_stage": "knockout",
                "diagnostic_value": "0-0_or_1-1_actuals",
                "knockout_matches": len(frame),
                "actual_matches": len(low_draw_rows),
                "top3_inclusion_matches": int(top3_low_draw_hits.sum()),
                "top3_inclusion_rate": float(top3_low_draw_hits.mean()),
                "actual_top3_hits": int(low_draw_rows["actual_scoreline_in_top_3"].sum()),
                "actual_top3_hit_rate": float(
                    low_draw_rows["actual_scoreline_in_top_3"].mean()
                    if not low_draw_rows.empty
                    else 0.0
                ),
                "avg_actual_scoreline_probability": float(
                    low_draw_rows["actual_scoreline_probability"].mean()
                    if not low_draw_rows.empty
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def build_upset_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    working = add_confederation_diagnostics(predictions)
    misses = working.loc[~working["is_correct_prediction"]].copy()
    columns = [
        "world_cup_year",
        "backtest_stage",
        "match_date",
        "home_team",
        "away_team",
        "home_confederation",
        "away_confederation",
        "home_score",
        "away_score",
        "actual_outcome",
        "predicted_outcome",
        "top_probability",
        "actual_outcome_probability",
        "row_log_loss",
        "confidence_bucket",
        "confederation_pair",
        "favorite_matchup_profile",
        "is_high_confidence_miss",
    ]
    return misses.sort_values("row_log_loss", ascending=False)[columns].reset_index(drop=True)


def prepare_backtest_diagnostics(
    *,
    years: tuple[int, ...] = (2018, 2022),
) -> DiagnosticOutputs:
    ensure_project_directories()
    ensure_diagnostic_inputs(years)

    predictions = pd.read_csv(WORLD_CUP_BACKTEST_PREDICTIONS_PATH)
    calibration = build_calibration_diagnostics(predictions)
    confederation = build_confederation_diagnostics(predictions)
    low_score = build_low_score_diagnostics(predictions)
    upset = build_upset_diagnostics(predictions)

    calibration.to_csv(WORLD_CUP_BACKTEST_CALIBRATION_PATH, index=False, encoding="utf-8-sig")
    confederation.to_csv(WORLD_CUP_BACKTEST_CONFEDERATION_PATH, index=False, encoding="utf-8-sig")
    low_score.to_csv(WORLD_CUP_BACKTEST_LOW_SCORE_PATH, index=False, encoding="utf-8-sig")
    upset.to_csv(WORLD_CUP_BACKTEST_UPSET_PATH, index=False, encoding="utf-8-sig")

    return DiagnosticOutputs(
        calibration_path=str(WORLD_CUP_BACKTEST_CALIBRATION_PATH),
        confederation_path=str(WORLD_CUP_BACKTEST_CONFEDERATION_PATH),
        low_score_path=str(WORLD_CUP_BACKTEST_LOW_SCORE_PATH),
        upset_path=str(WORLD_CUP_BACKTEST_UPSET_PATH),
        calibration_rows=len(calibration),
        confederation_rows=len(confederation),
        low_score_rows=len(low_score),
        upset_rows=len(upset),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build World Cup backtest diagnostic reports.")
    parser.add_argument("--years", nargs="+", type=int, default=[2018, 2022])
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_backtest_diagnostics(years=tuple(args.years))
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
