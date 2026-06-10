import pandas as pd

from src.analysis_diagnostics import (
    build_calibration_diagnostics,
    build_confederation_diagnostics,
    build_low_score_diagnostics,
    build_upset_diagnostics,
    top3_contains,
)


def sample_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "world_cup_year": [2022, 2022, 2022],
            "backtest_stage": ["group_stage", "group_stage", "knockout"],
            "match_date": ["2022-11-22", "2022-11-23", "2022-12-09"],
            "home_team": ["Argentina", "Germany", "Netherlands"],
            "away_team": ["Saudi Arabia", "Japan", "Argentina"],
            "home_score": [1, 1, 2],
            "away_score": [2, 2, 2],
            "actual_outcome": ["away_win", "away_win", "draw"],
            "predicted_outcome": ["home_win", "home_win", "draw"],
            "away_win_probability": [0.12, 0.18, 0.31],
            "draw_probability": [0.18, 0.22, 0.39],
            "home_win_probability": [0.70, 0.60, 0.30],
            "actual_outcome_probability": [0.12, 0.18, 0.39],
            "actual_scoreline": ["1-2", "1-2", "2-2"],
            "actual_scoreline_probability": [0.04, 0.05, 0.03],
            "top3_scorelines": ["1-0|2-0|1-1", "1-0|2-1|1-1", "1-1|0-0|2-1"],
            "actual_scoreline_in_top_3": [False, False, False],
        }
    )


def test_top3_contains_splits_pipe_delimited_scorelines() -> None:
    assert top3_contains("1-0|0-0|1-1", "0-0")
    assert not top3_contains("1-0|2-0|1-1", "0-0")


def test_build_calibration_diagnostics_returns_top_class_bins() -> None:
    diagnostics = build_calibration_diagnostics(sample_predictions())

    assert "top_class_confidence" in set(diagnostics["calibration_type"])
    assert diagnostics["matches"].sum() >= len(sample_predictions())


def test_build_confederation_diagnostics_flags_region_pairs() -> None:
    diagnostics = build_confederation_diagnostics(sample_predictions())

    pairs = diagnostics.loc[
        diagnostics["diagnostic_dimension"] == "confederation_pair",
        "diagnostic_value",
    ]
    assert "AFC_vs_CONMEBOL" in set(pairs)


def test_build_low_score_diagnostics_measures_knockout_top3_coverage() -> None:
    diagnostics = build_low_score_diagnostics(sample_predictions())

    zero_zero = diagnostics.loc[diagnostics["diagnostic_value"] == "0-0"].iloc[0]
    assert zero_zero["top3_inclusion_matches"] == 1


def test_build_upset_diagnostics_sorts_misses_by_log_loss() -> None:
    diagnostics = build_upset_diagnostics(sample_predictions())

    assert diagnostics.iloc[0]["home_team"] == "Argentina"
    assert diagnostics.iloc[0]["is_high_confidence_miss"]
