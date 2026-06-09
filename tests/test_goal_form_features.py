import pandas as pd

from src.goal_form_features import build_team_goal_form_features, build_team_match_goal_rows


def test_build_team_match_goal_rows_creates_two_rows_per_match() -> None:
    matches = pd.DataFrame(
        {
            "match_id": [1],
            "match_date": [pd.Timestamp("2024-01-01").date()],
            "home_team": ["Brazil"],
            "away_team": ["Morocco"],
            "home_score": [2],
            "away_score": [1],
            "competition_type": ["world_cup"],
        }
    )

    rows = build_team_match_goal_rows(matches)

    assert len(rows) == 2
    assert rows.loc[rows["team_name"] == "Brazil", "goals_for"].item() == 2.0
    assert rows.loc[rows["team_name"] == "Morocco", "goals_against"].item() == 2.0


def test_build_team_goal_form_features_summarizes_latest_windows() -> None:
    matches = pd.DataFrame(
        {
            "match_id": [1, 2, 3],
            "match_date": [
                pd.Timestamp("2024-01-01").date(),
                pd.Timestamp("2024-02-01").date(),
                pd.Timestamp("2024-03-01").date(),
            ],
            "home_team": ["Brazil", "Brazil", "Brazil"],
            "away_team": ["A", "B", "C"],
            "home_score": [2, 0, 3],
            "away_score": [0, 1, 1],
            "competition_type": ["world_cup", "friendly", "world_cup"],
        }
    )

    features = build_team_goal_form_features(matches)
    brazil = features.loc[features["team_name"] == "Brazil"].iloc[0]

    assert brazil["matches_played"] == 3
    assert round(brazil["goals_for_last_5"], 3) == 1.667
    assert round(brazil["goals_against_last_5"], 3) == 0.667
    assert round(brazil["clean_sheet_rate_last_5"], 3) == 0.333
