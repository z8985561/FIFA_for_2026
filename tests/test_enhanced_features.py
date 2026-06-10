import pandas as pd

from src.enhanced_features import (
    build_2026_enhanced_features,
    build_historical_enhanced_features,
    enhanced_feature_columns,
)


def test_historical_features_use_only_prior_team_form() -> None:
    matches = pd.DataFrame(
        {
            "match_id": [1, 2],
            "match_date": [pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-02-01").date()],
            "home_team": ["Brazil", "Brazil"],
            "away_team": ["Morocco", "Spain"],
            "home_score": [2, 1],
            "away_score": [0, 1],
            "competition_type": ["friendly", "world_cup"],
            "outcome": ["home_win", "draw"],
            "elo_diff": [50.0, 20.0],
            "expected_home_win": [0.57, 0.53],
            "neutral": [True, True],
            "home_rest_days": [None, 31.0],
            "away_rest_days": [None, None],
        }
    )

    features = build_historical_enhanced_features(matches)

    assert set(enhanced_feature_columns()).issubset(features.columns)
    assert features.loc[0, "home_matches_last_5"] == 0.0
    assert features.loc[1, "home_points_per_match_last_5"] == 3.0
    assert features.loc[1, "home_goal_diff_per_match_last_5"] == 2.0
    assert features.loc[1, "away_points_per_match_last_5"] == 1.0
    assert features.loc[0, "home_confederation"] == "CONMEBOL"
    assert features.loc[0, "away_confederation"] == "CAF"
    assert features.loc[0, "confed_pair_CAF_vs_CONMEBOL"] == 1


def test_2026_features_merge_latest_form_and_fixture_rest_days() -> None:
    historical = pd.DataFrame(
        {
            "match_id": [1, 2],
            "match_date": [pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-02-01").date()],
            "home_team": ["Brazil", "Morocco"],
            "away_team": ["Morocco", "Brazil"],
            "home_score": [2, 0],
            "away_score": [0, 1],
            "competition_type": ["world_cup", "world_cup"],
            "outcome": ["home_win", "away_win"],
            "elo_diff": [80.0, -60.0],
            "expected_home_win": [0.62, 0.41],
            "neutral": [True, True],
            "home_rest_days": [None, 31.0],
            "away_rest_days": [None, 31.0],
        }
    )
    match_features = pd.DataFrame(
        {
            "match_no": [1, 2],
            "stage": ["Group Stage", "Group Stage"],
            "group_name": ["Group C", "Group C"],
            "date_et": [pd.Timestamp("2026-06-13").date(), pd.Timestamp("2026-06-18").date()],
            "home_team": ["Brazil", "Brazil"],
            "away_team": ["Morocco", "Spain"],
            "home_latest_elo": [1926.0, 1926.0],
            "away_latest_elo": [1837.0, 1974.0],
            "elo_diff": [89.0, -48.0],
            "expected_home_win": [0.63, 0.43],
            "neutral": [True, True],
        }
    )

    features = build_2026_enhanced_features(match_features, historical)

    assert features.loc[0, "home_rest_days"] == 30.0
    assert features.loc[1, "home_rest_days"] == 5.0
    assert features.loc[0, "home_points_per_match_last_5"] == 3.0
    assert features.loc[1, "away_matches_last_5"] == 0.0
    assert features.loc[0, "home_confederation"] == "CONMEBOL"
    assert features.loc[0, "away_confederation"] == "CAF"
    assert features.loc[0, "cross_confederation_int"] == 1
