import pandas as pd

from src.enhanced_model import combine_match_odds_feature_sources
from src.market_features import attach_market_features, blend_model_and_market_probabilities


def test_blend_model_and_market_probabilities_returns_normalized_rows() -> None:
    model_probabilities = pd.DataFrame(
        {
            "away_win_probability": [0.20],
            "draw_probability": [0.30],
            "home_win_probability": [0.50],
        }
    )
    market_features = pd.DataFrame(
        {
            "consensus_away_win_probability": [0.25],
            "consensus_draw_probability": [0.25],
            "consensus_home_win_probability": [0.50],
        }
    )

    blended = blend_model_and_market_probabilities(
        model_probabilities,
        market_features,
        model_weight=0.6,
    )

    assert round(float(blended.sum(axis=1).iloc[0]), 8) == 1.0
    assert round(float(blended.loc[0, "blended_away_win_probability"]), 8) == 0.22


def test_attach_market_features_merges_market_probabilities_and_gaps() -> None:
    predictions = pd.DataFrame(
        {
            "match_no": [1, 2],
            "date_et": [pd.Timestamp("2026-06-11").date(), pd.Timestamp("2026-06-12").date()],
            "home_team": ["Mexico", "Canada"],
            "away_team": ["South Africa", "Japan"],
            "away_win_probability": [0.10, 0.25],
            "draw_probability": [0.20, 0.30],
            "home_win_probability": [0.70, 0.45],
            "predicted_outcome": ["home_win", "home_win"],
        }
    )
    market_odds_features = pd.DataFrame(
        {
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "commence_time": [pd.Timestamp("2026-06-11T19:00:00Z")],
            "consensus_home_win_probability": [0.65],
            "consensus_draw_probability": [0.22],
            "consensus_away_win_probability": [0.13],
            "avg_market_overround": [0.04],
            "min_market_overround": [0.02],
            "max_market_overround": [0.06],
            "bookmaker_count": [20],
            "latest_bookmaker_update": [pd.Timestamp("2026-06-10T02:35:00Z")],
            "latest_market_update": [pd.Timestamp("2026-06-10T02:35:00Z")],
            "latest_fetched_at": [pd.Timestamp("2026-06-10T02:36:00Z")],
            "market_entropy": [0.85],
            "favorite_probability": [0.65],
            "favorite_outcome": ["home_win"],
        }
    )

    attached = attach_market_features(predictions, market_odds_features)

    assert bool(attached.loc[0, "has_market_odds"]) is True
    assert bool(attached.loc[1, "has_market_odds"]) is False
    assert round(float(attached.loc[0, "model_market_home_gap"]), 8) == 0.05
    assert round(float(attached.loc[1, "blended_home_win_probability"]), 8) == 0.45
    assert attached.loc[0, "blended_predicted_outcome"] == "home_win"


def test_attach_market_features_matches_reversed_market_home_away_order() -> None:
    predictions = pd.DataFrame(
        {
            "match_date": [pd.Timestamp("2022-11-22").date()],
            "home_team": ["Argentina"],
            "away_team": ["Saudi Arabia"],
            "away_win_probability": [0.05],
            "draw_probability": [0.15],
            "home_win_probability": [0.80],
            "predicted_outcome": ["home_win"],
        }
    )
    market_odds_features = pd.DataFrame(
        {
            "home_team": ["Saudi Arabia"],
            "away_team": ["Argentina"],
            "commence_time": [pd.Timestamp("2022-11-22T10:00:00Z")],
            "consensus_home_win_probability": [0.08],
            "consensus_draw_probability": [0.17],
            "consensus_away_win_probability": [0.75],
            "avg_market_overround": [0.04],
            "min_market_overround": [0.03],
            "max_market_overround": [0.05],
            "bookmaker_count": [18],
            "latest_bookmaker_update": [pd.Timestamp("2022-11-22T09:00:00Z")],
            "latest_market_update": [pd.Timestamp("2022-11-22T09:00:00Z")],
            "latest_fetched_at": [pd.Timestamp("2022-11-22T09:05:00Z")],
            "market_entropy": [0.72],
            "favorite_probability": [0.75],
            "favorite_outcome": ["away_win"],
        }
    )

    attached = attach_market_features(
        predictions,
        market_odds_features,
        prediction_date_column="match_date",
        market_date_timezone="UTC",
    )

    assert bool(attached.loc[0, "has_market_odds"]) is True
    assert round(float(attached.loc[0, "consensus_home_win_probability"]), 8) == 0.75
    assert round(float(attached.loc[0, "consensus_away_win_probability"]), 8) == 0.08


def test_combine_match_odds_feature_sources_prefers_sporttery_for_same_match() -> None:
    base = pd.DataFrame(
        {
            "event_id": ["market_1"],
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "commence_time": [pd.Timestamp("2026-06-11T18:00:00Z")],
            "consensus_home_win_probability": [0.60],
            "consensus_draw_probability": [0.25],
            "consensus_away_win_probability": [0.15],
        }
    )
    sporttery = pd.DataFrame(
        {
            "event_id": ["sporttery_2040162"],
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "commence_time": [pd.Timestamp("2026-06-11T12:00:00Z")],
            "consensus_home_win_probability": [0.68],
            "consensus_draw_probability": [0.21],
            "consensus_away_win_probability": [0.11],
        }
    )

    combined = combine_match_odds_feature_sources(base, sporttery)

    assert len(combined) == 1
    assert combined.loc[0, "event_id"] == "sporttery_2040162"
    assert round(float(combined.loc[0, "consensus_home_win_probability"]), 8) == 0.68


def test_combine_match_odds_feature_sources_deduplicates_reversed_team_order() -> None:
    base = pd.DataFrame(
        {
            "event_id": ["market_1", "market_1_reversed"],
            "home_team": ["Tunisia", "Sweden"],
            "away_team": ["Sweden", "Tunisia"],
            "commence_time": [
                pd.Timestamp("2026-06-14T18:00:00Z"),
                pd.Timestamp("2026-06-14T18:00:00Z"),
            ],
            "consensus_home_win_probability": [0.30, 0.40],
            "consensus_draw_probability": [0.30, 0.30],
            "consensus_away_win_probability": [0.40, 0.30],
        }
    )

    combined = combine_match_odds_feature_sources(base, pd.DataFrame())

    assert len(combined) == 1
