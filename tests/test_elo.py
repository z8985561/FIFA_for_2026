import pandas as pd

from src.elo import build_elo_features, classify_outcome


def test_classify_outcome() -> None:
    assert classify_outcome(2, 0) == "home_win"
    assert classify_outcome(0, 1) == "away_win"
    assert classify_outcome(1, 1) == "draw"


def test_build_elo_features_adds_expected_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "home_team": "Alpha",
                "away_team": "Beta",
                "home_score": 2,
                "away_score": 1,
                "tournament": "Friendly",
                "city": "A",
                "country": "A",
                "neutral": False,
            },
            {
                "date": "2024-01-10",
                "home_team": "Beta",
                "away_team": "Alpha",
                "home_score": 0,
                "away_score": 0,
                "tournament": "Friendly",
                "city": "B",
                "country": "B",
                "neutral": True,
            },
        ]
    )
    frame["date"] = pd.to_datetime(frame["date"])

    result = build_elo_features(frame)

    assert {"pre_match_elo_home", "pre_match_elo_away", "elo_diff", "outcome"}.issubset(
        result.columns
    )
    assert result.loc[0, "outcome"] == "home_win"
    assert result.loc[1, "outcome"] == "draw"
