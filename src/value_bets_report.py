from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .project_paths import (
    SCORE_ODDS_FEATURES_PATH,
    SCORELINE_ANALYSIS_PATH,
    SCORELINE_VALUE_BETS_PATH,
    ensure_project_directories,
)
from .score_odds_pipeline import prepare_score_odds_features
from .scoreline_model import prepare_scoreline_analysis


@dataclass(frozen=True)
class ValueBetsReportOutputs:
    value_bets_path: str
    rows: int
    matched_odds_rows: int
    positive_edge_rows: int


def ensure_value_report_inputs(*, match_limit: int) -> None:
    if not SCORELINE_ANALYSIS_PATH.exists():
        prepare_scoreline_analysis(limit=match_limit)
    if not SCORE_ODDS_FEATURES_PATH.exists():
        prepare_score_odds_features(match_limit=match_limit)


def kelly_fraction(probability: pd.Series, decimal_odds: pd.Series) -> pd.Series:
    probability_values = pd.to_numeric(probability, errors="coerce").to_numpy(dtype=float)
    decimal_odds_values = pd.to_numeric(decimal_odds, errors="coerce").to_numpy(dtype=float)
    net_odds = decimal_odds_values - 1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = (probability_values * decimal_odds_values - 1.0) / net_odds
    clean = np.where(np.isfinite(raw), raw, 0.0)
    return pd.Series(clean, index=probability.index).fillna(0.0).clip(lower=0.0)


def build_scoreline_value_bets(
    scoreline_analysis: pd.DataFrame,
    score_odds_features: pd.DataFrame,
) -> pd.DataFrame:
    if scoreline_analysis.empty:
        return pd.DataFrame()

    odds_columns = [
        "match_no",
        "scoreline",
        "best_decimal_odds",
        "average_decimal_odds",
        "raw_market_implied_probability",
        "listed_score_fair_probability",
        "listed_score_market_overround_proxy",
        "bookmaker_count",
        "source_names",
        "source_urls",
        "source_match_ids",
        "latest_fetched_at",
    ]
    if score_odds_features.empty:
        score_odds_features = pd.DataFrame(columns=odds_columns)
    for column in odds_columns:
        if column not in score_odds_features.columns:
            score_odds_features[column] = pd.NA

    merged = scoreline_analysis.merge(
        score_odds_features[odds_columns],
        on=["match_no", "scoreline"],
        how="left",
    )
    merged["model_probability"] = merged["scoreline_probability"]
    merged["model_fair_odds"] = 1.0 / merged["model_probability"].clip(lower=1e-12)
    merged["market_edge"] = (
        merged["model_probability"] * merged["best_decimal_odds"] - 1.0
    )
    merged["kelly_fraction"] = kelly_fraction(
        merged["model_probability"],
        merged["best_decimal_odds"],
    )
    merged["has_score_odds"] = merged["best_decimal_odds"].notna()
    merged["value_signal"] = np.select(
        [
            ~merged["has_score_odds"],
            merged["market_edge"] >= 0.10,
            merged["market_edge"] > 0.0,
        ],
        ["missing_odds", "strong_value", "thin_value"],
        default="no_value",
    )
    sorted_report = merged.sort_values(
        ["has_score_odds", "market_edge", "model_probability"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    output_columns = [
        "match_no",
        "stage",
        "group_name",
        "date_et",
        "home_team",
        "away_team",
        "home_team_zh",
        "away_team_zh",
        "scoreline_rank",
        "scoreline",
        "model_probability",
        "model_fair_odds",
        "best_decimal_odds",
        "average_decimal_odds",
        "raw_market_implied_probability",
        "listed_score_fair_probability",
        "listed_score_market_overround_proxy",
        "market_edge",
        "kelly_fraction",
        "has_score_odds",
        "value_signal",
        "bookmaker_count",
        "source_names",
        "source_urls",
        "source_match_ids",
        "latest_fetched_at",
    ]
    return sorted_report[output_columns]


def prepare_value_bets_report(
    *,
    match_limit: int = 4,
    output_path=SCORELINE_VALUE_BETS_PATH,
) -> ValueBetsReportOutputs:
    ensure_project_directories()
    ensure_value_report_inputs(match_limit=match_limit)
    scoreline_analysis = pd.read_csv(SCORELINE_ANALYSIS_PATH)
    score_odds_features = (
        pd.read_parquet(SCORE_ODDS_FEATURES_PATH)
        if SCORE_ODDS_FEATURES_PATH.exists()
        else pd.DataFrame()
    )
    report = build_scoreline_value_bets(scoreline_analysis, score_odds_features)
    report.to_csv(output_path, index=False, encoding="utf-8-sig")
    return ValueBetsReportOutputs(
        value_bets_path=str(output_path),
        rows=len(report),
        matched_odds_rows=int(report["has_score_odds"].sum()) if not report.empty else 0,
        positive_edge_rows=int(report["market_edge"].gt(0).sum()) if not report.empty else 0,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build exact-score value-bet report.")
    parser.add_argument("--limit", type=int, default=4)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_value_bets_report(match_limit=args.limit)
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
