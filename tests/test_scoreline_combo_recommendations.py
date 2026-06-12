import pandas as pd

from src.scoreline_combo_recommendations import (
    build_match_outcome_summary,
    build_upset_scoreline_candidates,
    rank_upset_combos,
)


def sample_scoreline_analysis() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "match_no": [1, 1, 1, 2, 2, 2],
            "home_team": ["Alpha", "Alpha", "Alpha", "Gamma", "Gamma", "Gamma"],
            "away_team": ["Beta", "Beta", "Beta", "Delta", "Delta", "Delta"],
            "home_team_zh": ["Alpha", "Alpha", "Alpha", "Gamma", "Gamma", "Gamma"],
            "away_team_zh": ["Beta", "Beta", "Beta", "Delta", "Delta", "Delta"],
            "score_home_win_probability": [0.62, 0.62, 0.62, 0.33, 0.33, 0.33],
            "score_draw_probability": [0.22, 0.22, 0.22, 0.27, 0.27, 0.27],
            "score_away_win_probability": [0.16, 0.16, 0.16, 0.40, 0.40, 0.40],
            "scoreline": ["1-0", "0-1", "1-2", "1-0", "2-1", "0-1"],
            "scoreline_probability": [0.11, 0.05, 0.04, 0.08, 0.09, 0.07],
        }
    )


def sample_value_bets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "match_no": [1, 1, 2, 2],
            "home_team": ["Alpha", "Alpha", "Gamma", "Gamma"],
            "away_team": ["Beta", "Beta", "Delta", "Delta"],
            "home_team_zh": ["Alpha", "Alpha", "Gamma", "Gamma"],
            "away_team_zh": ["Beta", "Beta", "Delta", "Delta"],
            "scoreline": ["0-1", "1-2", "1-0", "2-1"],
            "model_probability": [0.05, 0.04, 0.08, 0.09],
            "best_decimal_odds": [12.0, 18.0, 7.5, 9.0],
            "value_signal": ["thin_value", "strong_value", "no_value", "thin_value"],
            "has_score_odds": [True, True, True, True],
        }
    )


def test_build_match_outcome_summary_identifies_favorite_and_underdog() -> None:
    summary = build_match_outcome_summary(sample_scoreline_analysis())

    assert list(summary["favorite_outcome"]) == ["home_win", "away_win"]
    assert list(summary["underdog_outcome"]) == ["away_win", "home_win"]
    assert round(float(summary.loc[0, "underdog_probability"]), 4) == 0.16
    assert round(float(summary.loc[1, "favorite_probability"]), 4) == 0.40


def test_build_upset_scoreline_candidates_picks_best_underdog_scoreline() -> None:
    candidates = build_upset_scoreline_candidates(
        sample_scoreline_analysis(),
        sample_value_bets(),
    )

    assert list(candidates["scoreline"]) == ["0-1", "2-1"]
    assert round(float(candidates.loc[0, "best_decimal_odds"]), 1) == 12.0
    assert round(float(candidates.loc[1, "underdog_probability"]), 2) == 0.33


def test_rank_upset_combos_sorts_by_joint_upset_probability() -> None:
    ranked = rank_upset_combos(
        sample_scoreline_analysis(),
        sample_value_bets(),
        limit=1,
    )

    assert len(ranked) == 1
    assert ranked.loc[0, "leg_a_scoreline"] == "0-1"
    assert ranked.loc[0, "leg_b_scoreline"] == "2-1"
    assert round(float(ranked.loc[0, "joint_upset_probability"]), 4) == 0.0528
