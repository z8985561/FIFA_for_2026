import pandas as pd

from src.scoreline_model import (
    add_group_match_rounds,
    apply_group_opener_mismatch_adjustment,
    apply_lineup_goal_rate_adjustment,
    apply_market_scoreline_constraints,
    apply_suspension_goal_rate_adjustment,
    build_scoreline_market_constraints,
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


def test_apply_suspension_goal_rate_adjustment_penalizes_missing_attackers() -> None:
    adjusted = apply_suspension_goal_rate_adjustment(
        home_goal_rate=1.5,
        away_goal_rate=1.0,
        home_suspensions={
            "suspended_attack_impact": 0.05,
            "suspended_defense_impact": 0.0,
            "suspended_count": 1,
        },
        away_suspensions={
            "suspended_attack_impact": 0.0,
            "suspended_defense_impact": 0.03,
            "suspended_count": 1,
        },
    )

    assert adjusted["home_expected_goals"] < 1.5
    assert adjusted["away_expected_goals"] == 1.0
    assert adjusted["home_suspension_goal_factor"] < 1.0


def test_add_group_match_rounds_assigns_two_matches_per_group_round() -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [1, 2, 3, 4, 5],
            "group_name": ["Group A", "Group A", "Group A", "Group A", "Group B"],
            "date_et": pd.to_datetime(
                [
                    "2026-06-11",
                    "2026-06-11",
                    "2026-06-16",
                    "2026-06-16",
                    "2026-06-12",
                ]
            ),
        }
    )

    enriched = add_group_match_rounds(fixtures)

    assert enriched.loc[enriched["match_no"].eq(1), "group_match_round"].item() == 1
    assert enriched.loc[enriched["match_no"].eq(2), "group_match_round"].item() == 1
    assert enriched.loc[enriched["match_no"].eq(3), "group_match_round"].item() == 2
    assert enriched.loc[enriched["match_no"].eq(5), "group_match_round"].item() == 1


def test_apply_group_opener_mismatch_adjustment_boosts_only_first_round_favorite() -> None:
    adjusted = apply_group_opener_mismatch_adjustment(
        home_goal_rate=1.5,
        away_goal_rate=0.8,
        stage="Group Stage",
        group_match_round=1,
        elo_diff=180.0,
        home_team="Mexico",
        away_team="South Africa",
    )
    unchanged = apply_group_opener_mismatch_adjustment(
        home_goal_rate=1.5,
        away_goal_rate=0.8,
        stage="Group Stage",
        group_match_round=2,
        elo_diff=180.0,
        home_team="Mexico",
        away_team="South Africa",
    )

    assert adjusted["group_opener_mismatch_adjustment_applied"] is True
    assert adjusted["group_opener_favorite_team"] == "Mexico"
    assert adjusted["home_expected_goals"] > 1.5
    assert adjusted["away_expected_goals"] == 0.8
    assert unchanged["group_opener_mismatch_adjustment_applied"] is False
    assert unchanged["home_expected_goals"] == 1.5


def test_build_scoreline_market_constraints_normalizes_had_and_ttg() -> None:
    snapshots = pd.DataFrame(
        {
            "match_no": [1, 1, 1, 1, 1],
            "market_code": ["HAD", "HAD", "HAD", "TTG", "TTG"],
            "outcome_code": ["home_win", "draw", "away_win", "total_goals_0", "total_goals_1"],
            "decimal_odds": [1.5, 4.0, 7.5, 8.0, 4.0],
        }
    )

    constraints = build_scoreline_market_constraints(snapshots)

    assert bool(constraints.loc[0, "has_market_outcome_constraint"]) is True
    assert bool(constraints.loc[0, "has_market_total_goals_constraint"]) is True
    had_sum = (
        constraints.loc[0, "market_home_win_probability"]
        + constraints.loc[0, "market_draw_probability"]
        + constraints.loc[0, "market_away_win_probability"]
    )
    assert round(float(had_sum), 8) == 1.0


def test_apply_market_scoreline_constraints_moves_marginals_toward_market() -> None:
    matrix = scoreline_matrix(1.0, 1.0, max_goals=5)
    before = matrix_summary(matrix)
    constraint = {
        "has_market_outcome_constraint": True,
        "market_home_win_probability": 0.70,
        "market_draw_probability": 0.20,
        "market_away_win_probability": 0.10,
        "has_market_total_goals_constraint": True,
        "market_total_goals_probabilities": {
            "total_goals_0": 0.30,
            "total_goals_1": 0.30,
            "total_goals_2": 0.20,
            "total_goals_3": 0.10,
            "total_goals_4": 0.05,
            "total_goals_5": 0.03,
            "total_goals_6": 0.01,
            "total_goals_7_plus": 0.01,
        },
    }

    adjusted = apply_market_scoreline_constraints(matrix, constraint)
    after = matrix_summary(adjusted)

    assert round(adjusted["probability"].sum(), 8) == 1.0
    assert after["score_home_win_probability"] > before["score_home_win_probability"]
    assert after["over_2_5_probability"] < before["over_2_5_probability"]
