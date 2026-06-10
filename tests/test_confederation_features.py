import pandas as pd

from src.confederation_features import (
    add_confederation_features,
    confederation_feature_columns,
    confederation_pair,
    team_confederation,
)


def test_team_confederation_uses_historical_world_cup_mapping() -> None:
    assert team_confederation("Cameroon") == "CAF"
    assert team_confederation("Argentina") == "CONMEBOL"
    assert team_confederation("Atlantis") == "UNKNOWN"


def test_confederation_pair_is_order_invariant() -> None:
    assert confederation_pair("CONMEBOL", "AFC") == "AFC_vs_CONMEBOL"
    assert confederation_pair("AFC", "CONMEBOL") == "AFC_vs_CONMEBOL"


def test_add_confederation_features_builds_model_ready_columns() -> None:
    frame = pd.DataFrame(
        {
            "home_team": ["Argentina", "Japan"],
            "away_team": ["Saudi Arabia", "South Korea"],
            "elo_diff": [120.0, 20.0],
        }
    )

    features = add_confederation_features(frame)

    assert set(confederation_feature_columns()).issubset(features.columns)
    assert features.loc[0, "cross_confederation_int"] == 1
    assert features.loc[0, "elo_diff_cross_confed"] == 120.0
    assert features.loc[1, "same_confederation_int"] == 1
    assert features.loc[1, "elo_diff_cross_confed"] == 0.0
    assert features.loc[0, "confed_pair_AFC_vs_CONMEBOL"] == 1
