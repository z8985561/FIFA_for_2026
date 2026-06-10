import pandas as pd

from src.world_cup_backtest import (
    add_world_cup_stage_labels,
    aggregate_metrics,
    world_cup_finals,
)


def test_world_cup_finals_excludes_qualifiers() -> None:
    matches = pd.DataFrame(
        {
            "match_id": [1, 2],
            "match_date": [pd.Timestamp("2022-03-01").date(), pd.Timestamp("2022-11-20").date()],
            "tournament": ["FIFA World Cup qualification", "FIFA World Cup"],
        }
    )

    finals = world_cup_finals(matches, 2022)

    assert len(finals) == 1
    assert finals.iloc[0]["match_id"] == 2


def test_add_world_cup_stage_labels_splits_first_48_as_group_stage() -> None:
    finals = pd.DataFrame(
        {
            "match_id": list(range(1, 65)),
            "match_date": [pd.Timestamp("2022-11-20").date()] * 64,
        }
    )

    labelled = add_world_cup_stage_labels(finals)

    assert labelled.loc[47, "backtest_stage"] == "group_stage"
    assert labelled.loc[48, "backtest_stage"] == "knockout"


def test_aggregate_metrics_returns_all_and_stage_rows() -> None:
    predictions = pd.DataFrame(
        {
            "world_cup_year": [2022, 2022],
            "backtest_stage": ["group_stage", "knockout"],
            "actual_outcome": ["home_win", "draw"],
            "predicted_outcome": ["home_win", "draw"],
            "away_win_probability": [0.1, 0.2],
            "draw_probability": [0.2, 0.6],
            "home_win_probability": [0.7, 0.2],
            "home_score": [2, 1],
            "away_score": [0, 1],
            "home_expected_goals": [1.8, 1.1],
            "away_expected_goals": [0.7, 1.0],
            "actual_scoreline_probability": [0.12, 0.1],
            "actual_scoreline_in_top_1": [True, False],
            "actual_scoreline_in_top_3": [True, True],
            "actual_over_2_5": [0, 0],
            "over_2_5_probability": [0.4, 0.45],
            "actual_btts": [0, 1],
            "both_teams_score_probability": [0.35, 0.55],
        }
    )

    metrics = aggregate_metrics(predictions)

    assert set(metrics["backtest_stage"]) == {"all", "group_stage", "knockout"}
    assert metrics.loc[metrics["backtest_stage"] == "all", "matches"].item() == 2
