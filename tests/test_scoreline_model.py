import pandas as pd

from src.scoreline_model import matrix_summary, scoreline_matrix


def test_scoreline_matrix_normalizes_probabilities() -> None:
    matrix = scoreline_matrix(1.4, 0.9, max_goals=6)

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
