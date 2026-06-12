from __future__ import annotations

import pandas as pd

from src import match_review_pipeline as pipeline


def test_build_match_review_features_creates_review_buckets(tmp_path, monkeypatch) -> None:
    enhanced_path = tmp_path / "enhanced.csv"
    scorelines_path = tmp_path / "scorelines.csv"
    results_path = tmp_path / "official.parquet"

    pd.DataFrame(
        [
            {
                "match_no": 1,
                "stage": "Group Stage",
                "group_name": "Group A",
                "home_team": "Mexico",
                "away_team": "South Africa",
                "home_team_zh": "墨西哥",
                "away_team_zh": "南非",
                "predicted_outcome": "home_win",
                "blended_predicted_outcome": "home_win",
                "home_win_probability": 0.7,
                "draw_probability": 0.2,
                "away_win_probability": 0.1,
                "blended_home_win_probability": 0.72,
                "blended_draw_probability": 0.18,
                "blended_away_win_probability": 0.10,
            },
            {
                "match_no": 2,
                "stage": "Group Stage",
                "group_name": "Group A",
                "home_team": "South Korea",
                "away_team": "Czech Republic",
                "home_team_zh": "韩国",
                "away_team_zh": "捷克",
                "predicted_outcome": "draw",
                "blended_predicted_outcome": "draw",
                "home_win_probability": 0.3,
                "draw_probability": 0.5,
                "away_win_probability": 0.2,
                "blended_home_win_probability": 0.28,
                "blended_draw_probability": 0.52,
                "blended_away_win_probability": 0.20,
            },
        ]
    ).to_csv(enhanced_path, index=False)

    pd.DataFrame(
        [
            {
                "match_no": 1,
                "scoreline_rank": 1,
                "scoreline": "2-0",
                "scoreline_probability": 0.14,
                "home_expected_goals": 2.4,
                "away_expected_goals": 0.6,
                "score_home_win_probability": 0.75,
                "score_draw_probability": 0.17,
                "score_away_win_probability": 0.08,
            },
            {
                "match_no": 2,
                "scoreline_rank": 1,
                "scoreline": "1-1",
                "scoreline_probability": 0.13,
                "home_expected_goals": 1.2,
                "away_expected_goals": 1.0,
                "score_home_win_probability": 0.32,
                "score_draw_probability": 0.36,
                "score_away_win_probability": 0.32,
            },
        ]
    ).to_csv(scorelines_path, index=False)

    pd.DataFrame(
        [
            {
                "match_no": 1,
                "actual_home_score": 2,
                "actual_away_score": 0,
                "completed": True,
                "result_source_name": "FIFA Official API",
            },
            {
                "match_no": 2,
                "actual_home_score": 2,
                "actual_away_score": 1,
                "completed": True,
                "result_source_name": "FIFA Official API",
            },
        ]
    ).rename(
        columns={
            "actual_home_score": "home_score",
            "actual_away_score": "away_score",
            "result_source_name": "source_name",
        }
    ).to_parquet(results_path, index=False)

    monkeypatch.setattr(pipeline, "ENHANCED_PREDICTIONS_PATH", enhanced_path)
    monkeypatch.setattr(pipeline, "SCORELINE_ANALYSIS_PATH", scorelines_path)
    monkeypatch.setattr(pipeline, "OFFICIAL_MATCH_RESULTS_2026_PATH", results_path)

    review = pipeline.build_match_review_features()

    assert len(review) == 2

    match_one = review.loc[review["match_no"].eq(1)].iloc[0]
    assert bool(match_one["outcome_hit"]) is True
    assert bool(match_one["scoreline_hit"]) is True
    assert match_one["review_bucket"] == "exact_hit"
    assert match_one["actual_scoreline"] == "2-0"

    match_two = review.loc[review["match_no"].eq(2)].iloc[0]
    assert bool(match_two["outcome_hit"]) is False
    assert bool(match_two["scoreline_hit"]) is False
    assert match_two["review_bucket"] == "outcome_miss"
    assert match_two["actual_outcome"] == "home_win"
