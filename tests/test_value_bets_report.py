import pandas as pd

from src.value_bets_report import build_scoreline_value_bets


def test_build_scoreline_value_bets_calculates_edge_and_signal() -> None:
    scoreline_analysis = pd.DataFrame(
        {
            "match_no": [1],
            "stage": ["Group Stage"],
            "group_name": ["Group A"],
            "date_et": ["2026-06-11"],
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "home_team_zh": ["墨西哥"],
            "away_team_zh": ["南非"],
            "scoreline_rank": [1],
            "scoreline": ["2-0"],
            "scoreline_probability": [0.12],
        }
    )
    score_odds_features = pd.DataFrame(
        {
            "match_no": [1],
            "scoreline": ["2-0"],
            "best_decimal_odds": [10.0],
            "average_decimal_odds": [10.0],
            "raw_market_implied_probability": [0.1],
            "listed_score_fair_probability": [0.1],
            "listed_score_market_overround_proxy": [0.0],
            "bookmaker_count": [1],
            "source_names": ["中国体育彩票"],
            "source_urls": ["https://example.com"],
            "source_match_ids": ["2040162"],
            "latest_fetched_at": [pd.Timestamp("2026-06-10T00:00:00Z")],
        }
    )

    report = build_scoreline_value_bets(scoreline_analysis, score_odds_features)

    assert len(report) == 1
    assert report.loc[0, "has_score_odds"]
    assert round(report.loc[0, "market_edge"], 4) == 0.2
    assert report.loc[0, "value_signal"] == "strong_value"
    assert report.loc[0, "source_match_ids"] == "2040162"


def test_build_scoreline_value_bets_keeps_missing_odds_rows() -> None:
    scoreline_analysis = pd.DataFrame(
        {
            "match_no": [7],
            "stage": ["Group Stage"],
            "group_name": ["Group B"],
            "date_et": ["2026-06-12"],
            "home_team": ["Canada"],
            "away_team": ["Bosnia and Herzegovina"],
            "home_team_zh": ["加拿大"],
            "away_team_zh": ["波黑"],
            "scoreline_rank": [1],
            "scoreline": ["1-0"],
            "scoreline_probability": [0.10],
        }
    )

    report = build_scoreline_value_bets(scoreline_analysis, pd.DataFrame())

    assert len(report) == 1
    assert not report.loc[0, "has_score_odds"]
    assert report.loc[0, "value_signal"] == "missing_odds"
