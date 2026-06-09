import pandas as pd

from src.feature_store import build_group_difficulty_features, build_match_feature_store


def sample_team_profiles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "team_name": ["Brazil", "Morocco", "Scotland", "Haiti"],
            "group_name": ["Group C", "Group C", "Group C", "Group C"],
            "confederation": ["CONMEBOL", "CAF", "UEFA", "CONCACAF"],
            "fifa_rank": [6, 8, 43, 83],
            "latest_elo": [1926.04, 1837.26, 1690.63, 1600.07],
            "squad_size": [26, 26, 26, 26],
            "squad_average_age": [28.81, 25.92, 28.73, 27.08],
            "squad_total_caps": [916, 794, 973, 627],
            "matches_played": [1059, 617, 851, 510],
        }
    )


def test_build_group_difficulty_features_ranks_groups() -> None:
    profiles = pd.concat(
        [
            sample_team_profiles(),
            pd.DataFrame(
                {
                    "team_name": ["A", "B", "C", "D"],
                    "group_name": ["Group B"] * 4,
                    "confederation": ["UEFA"] * 4,
                    "fifa_rank": [50, 51, 52, 53],
                    "latest_elo": [1500.0, 1510.0, 1520.0, 1530.0],
                    "squad_size": [26] * 4,
                    "squad_average_age": [27.0] * 4,
                    "squad_total_caps": [500] * 4,
                    "matches_played": [300] * 4,
                }
            ),
        ],
        ignore_index=True,
    )

    difficulty = build_group_difficulty_features(profiles)

    group_c_rank = difficulty.loc[
        difficulty["group_name"] == "Group C", "group_difficulty_rank"
    ].item()
    group_b_rank = difficulty.loc[
        difficulty["group_name"] == "Group B", "group_difficulty_rank"
    ].item()

    assert group_c_rank == 1
    assert group_b_rank == 2


def test_build_match_feature_store_calculates_team_differences() -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [13],
            "stage": ["Group Stage"],
            "group_name": ["Group C"],
            "date_et": [pd.Timestamp("2026-06-13").date()],
            "home_team": ["Brazil"],
            "away_team": ["Morocco"],
            "venue": ["MetLife Stadium"],
            "city": ["New York New Jersey"],
        }
    )

    features = build_match_feature_store(fixtures, sample_team_profiles())
    row = features.iloc[0]

    assert row["match_no"] == 13
    assert row["home_rank_advantage"] == 2
    assert round(row["elo_diff"], 2) == 88.78
    assert row["squad_total_caps_diff"] == 122
    assert bool(row["same_confederation"]) is False
