from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass

import pandas as pd

from .project_paths import (
    ENHANCED_PREDICTIONS_PATH,
    MATCH_REVIEW_FEATURES_PATH,
    OFFICIAL_MATCH_RESULTS_2026_PATH,
    SCORELINE_ANALYSIS_PATH,
    ensure_project_directories,
)


@dataclass(frozen=True)
class MatchReviewOutputs:
    output_path: str
    review_rows: int
    completed_matches: int


def _read_table(path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _outcome_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def _review_bucket(row: pd.Series) -> str:
    if bool(row.get("outcome_hit")) and bool(row.get("scoreline_hit")):
        return "exact_hit"
    if bool(row.get("outcome_hit")):
        return "outcome_hit_only"
    probability = row.get("actual_outcome_probability")
    if probability is not None and pd.notna(probability) and float(probability) < 0.2:
        return "upset_miss"
    return "outcome_miss"


def build_match_review_features() -> pd.DataFrame:
    enhanced = _read_table(ENHANCED_PREDICTIONS_PATH)
    scorelines = _read_table(SCORELINE_ANALYSIS_PATH)
    official = _read_table(OFFICIAL_MATCH_RESULTS_2026_PATH)

    if enhanced.empty or scorelines.empty or official.empty:
        return pd.DataFrame()

    top_scorelines = (
        scorelines.loc[scorelines["scoreline_rank"].eq(1)].copy()
        if "scoreline_rank" in scorelines.columns
        else scorelines.copy()
    )
    top_scorelines = top_scorelines.rename(
        columns={
            "home_expected_goals": "expected_home_goals",
            "away_expected_goals": "expected_away_goals",
            "scoreline": "top_scoreline",
            "scoreline_probability": "top_scoreline_probability",
        }
    )

    official = official.copy()
    completed_col = official["completed"] if "completed" in official.columns else False
    official = official.loc[completed_col.fillna(False)].copy()
    if official.empty:
        return pd.DataFrame()

    official = official.rename(
        columns={
            "home_score": "actual_home_score",
            "away_score": "actual_away_score",
            "source_name": "result_source_name",
        }
    )

    keep_enhanced = [
        "match_no",
        "stage",
        "group_name",
        "home_team",
        "away_team",
        "home_team_zh",
        "away_team_zh",
        "predicted_outcome",
        "blended_predicted_outcome",
        "home_win_probability",
        "draw_probability",
        "away_win_probability",
        "blended_home_win_probability",
        "blended_draw_probability",
        "blended_away_win_probability",
    ]
    keep_enhanced = [column for column in keep_enhanced if column in enhanced.columns]

    keep_scores = [
        "match_no",
        "top_scoreline",
        "top_scoreline_probability",
        "expected_home_goals",
        "expected_away_goals",
        "score_home_win_probability",
        "score_draw_probability",
        "score_away_win_probability",
    ]
    keep_scores = [column for column in keep_scores if column in top_scorelines.columns]

    keep_official = [
        "match_no",
        "actual_home_score",
        "actual_away_score",
        "result_source_name",
    ]
    keep_official = [column for column in keep_official if column in official.columns]

    review = enhanced[keep_enhanced].merge(
        top_scorelines[keep_scores],
        on="match_no",
        how="left",
    )
    review = review.merge(
        official[keep_official],
        on="match_no",
        how="inner",
    )

    if review.empty:
        return review

    if "blended_predicted_outcome" in review.columns:
        review["predicted_outcome"] = review["blended_predicted_outcome"].fillna(
            review.get("predicted_outcome")
        )

    for source, target in (
        ("blended_home_win_probability", "predicted_home_win_probability"),
        ("blended_draw_probability", "predicted_draw_probability"),
        ("blended_away_win_probability", "predicted_away_win_probability"),
    ):
        if source in review.columns:
            review[target] = review[source]

    for source, target in (
        ("home_win_probability", "predicted_home_win_probability"),
        ("draw_probability", "predicted_draw_probability"),
        ("away_win_probability", "predicted_away_win_probability"),
    ):
        if target not in review.columns and source in review.columns:
            review[target] = review[source]
        elif source in review.columns:
            review[target] = review[target].fillna(review[source])

    review["actual_outcome"] = review.apply(
        lambda row: _outcome_label(int(row.actual_home_score), int(row.actual_away_score)),
        axis=1,
    )
    review["actual_scoreline"] = (
        review["actual_home_score"].astype(int).astype(str)
        + "-"
        + review["actual_away_score"].astype(int).astype(str)
    )
    review["expected_total_goals"] = (
        review.get("expected_home_goals", pd.Series(index=review.index, dtype=float)).fillna(0)
        + review.get("expected_away_goals", pd.Series(index=review.index, dtype=float)).fillna(0)
    )
    review["actual_total_goals"] = (
        review["actual_home_score"].astype(int) + review["actual_away_score"].astype(int)
    )
    review["outcome_hit"] = review["predicted_outcome"].eq(review["actual_outcome"])
    review["scoreline_hit"] = review["top_scoreline"].eq(review["actual_scoreline"])
    review["total_goals_error"] = review["actual_total_goals"] - review["expected_total_goals"]

    review["actual_outcome_probability"] = None
    review.loc[
        review["actual_outcome"].eq("home_win"),
        "actual_outcome_probability",
    ] = review.loc[review["actual_outcome"].eq("home_win"), "predicted_home_win_probability"]
    review.loc[
        review["actual_outcome"].eq("draw"),
        "actual_outcome_probability",
    ] = review.loc[review["actual_outcome"].eq("draw"), "predicted_draw_probability"]
    review.loc[
        review["actual_outcome"].eq("away_win"),
        "actual_outcome_probability",
    ] = review.loc[review["actual_outcome"].eq("away_win"), "predicted_away_win_probability"]

    review["review_bucket"] = review.apply(_review_bucket, axis=1)
    return review.sort_values("match_no").reset_index(drop=True)


def prepare_match_review_features() -> MatchReviewOutputs:
    ensure_project_directories()
    review = build_match_review_features()
    review.to_parquet(MATCH_REVIEW_FEATURES_PATH, index=False)
    return MatchReviewOutputs(
        output_path=str(MATCH_REVIEW_FEATURES_PATH),
        review_rows=len(review),
        completed_matches=len(review),
    )


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="Build match review feature table.")


def main() -> None:
    _ = build_parser().parse_args()
    outputs = prepare_match_review_features()
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
