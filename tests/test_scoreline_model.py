import pandas as pd

from src.scoreline_model import (
    apply_lineup_goal_rate_adjustment,
    dixon_coles_factor,
    inflate_scoreline_probability,
    lineup_adjustment_summary,
    matrix_summary,
    scoreline_matrix,
)


def test_scoreline_matrix_normalizes_probabilities() -> None:
    matrix = scoreline_matrix(1.4, 0.9, max_goals=6, rho=-0.03)

    assert round(matrix["probability"].sum(), 8) == 1.0
    assert {"home_goals", "away_goals", "scoreline", "probability"}.issubset(matrix.columns)


def test_matrix_summary_returns_market_style_probabilities() -> None:
    matrix = pd.DataFrame(
        {
            "home_goals": [1, 1, 0],
            "away_goals": [0, 1, 1],
            "probability": [0.5, 0.3, 0.2],
        }
    )

    summary = matrix_summary(matrix)

    assert summary["score_home_win_probability"] == 0.5
    assert summary["score_draw_probability"] == 0.3
    assert summary["score_away_win_probability"] == 0.2
    assert summary["both_teams_score_probability"] == 0.3


def test_dixon_coles_factor_adjusts_low_score_cells() -> None:
    assert dixon_coles_factor(0, 0, 1.4, 0.9, -0.03) > 1.0
    assert dixon_coles_factor(1, 1, 1.4, 0.9, -0.03) > 1.0
    assert dixon_coles_factor(2, 1, 1.4, 0.9, -0.03) == 1.0


def test_inflate_scoreline_probability_boosts_target_and_renormalizes() -> None:
    matrix = scoreline_matrix(1.2, 1.1, max_goals=4)
    before = matrix.loc[matrix["scoreline"] == "0-0", "probability"].item()

    adjusted = inflate_scoreline_probability(matrix, scoreline="0-0", multiplier=1.25)
    after = adjusted.loc[adjusted["scoreline"] == "0-0", "probability"].item()

    assert after > before
    assert round(adjusted["probability"].sum(), 8) == 1.0


def test_lineup_adjustment_summary_scores_key_starters() -> None:
    lineups = pd.DataFrame(
        {
            "match_no": [1, 1],
            "team_name": ["South Korea", "South Korea"],
            "lineup_status": ["predicted", "predicted"],
            "formation": ["4-2-3-1", "4-2-3-1"],
            "player_name": ["Son Heung-min", "Kim Min-jae"],
        }
    )

    summary = lineup_adjustment_summary(lineups)

    assert summary.loc[0, "lineup_attack_impact"] > 0
    assert summary.loc[0, "lineup_defense_impact"] > 0


def test_apply_lineup_goal_rate_adjustment_keeps_rates_positive() -> None:
    adjusted = apply_lineup_goal_rate_adjustment(
        home_goal_rate=1.5,
        away_goal_rate=1.0,
        home_lineup={"lineup_attack_impact": 0.08, "lineup_defense_impact": 0.03},
        away_lineup={"lineup_attack_impact": 0.02, "lineup_defense_impact": 0.01},
    )

    assert adjusted["home_expected_goals"] > 1.5
    assert adjusted["away_expected_goals"] < 1.0
    assert adjusted["home_lineup_goal_factor"] > 1.0
