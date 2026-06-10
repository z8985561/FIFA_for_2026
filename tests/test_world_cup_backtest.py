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


def test_aggregate_metrics_includes_market_and_blended_outcome_metrics() -> None:
    predictions = pd.DataFrame(
        {
            "world_cup_year": [2022, 2022],
            "backtest_stage": ["group_stage", "group_stage"],
            "actual_outcome": ["home_win", "away_win"],
            "predicted_outcome": ["home_win", "draw"],
            "away_win_probability": [0.1, 0.3],
            "draw_probability": [0.2, 0.4],
            "home_win_probability": [0.7, 0.3],
            "consensus_away_win_probability": [0.15, 0.55],
            "consensus_draw_probability": [0.25, 0.25],
            "consensus_home_win_probability": [0.60, 0.20],
            "has_market_odds": [True, True],
            "blended_away_win_probability": [0.12, 0.39],
            "blended_draw_probability": [0.22, 0.35],
            "blended_home_win_probability": [0.66, 0.26],
            "blended_predicted_outcome": ["home_win", "away_win"],
            "home_score": [2, 0],
            "away_score": [0, 1],
            "home_expected_goals": [1.8, 1.1],
            "away_expected_goals": [0.7, 1.0],
            "actual_scoreline_probability": [0.12, 0.1],
            "actual_scoreline_in_top_1": [True, False],
            "actual_scoreline_in_top_3": [True, True],
            "actual_over_2_5": [0, 0],
            "over_2_5_probability": [0.4, 0.45],
            "actual_btts": [0, 0],
            "both_teams_score_probability": [0.35, 0.55],
        }
    )

    metrics = aggregate_metrics(predictions)
    all_metrics = metrics.loc[metrics["backtest_stage"] == "all"].iloc[0]

    assert all_metrics["market_odds_matches"] == 2
    assert round(float(all_metrics["market_odds_coverage"]), 8) == 1.0
    assert round(float(all_metrics["market_outcome_accuracy"]), 8) == 1.0
    assert round(float(all_metrics["blended_outcome_accuracy"]), 8) == 1.0
