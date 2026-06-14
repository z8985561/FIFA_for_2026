from unittest.mock import patch

import pandas as pd

from src.apifootball_pipeline import fetch_fixtures, fetch_statistics, fetch_events

FIXTURE_PAYLOAD = {
    "response": [
        {
            "fixture": {
                "id": 855736,
                "date": "2022-11-20T16:00:00+00:00",
                "status": {"short": "FT", "elapsed": 90},
                "venue": {"name": "Al Bayt Stadium", "city": "Al Khor"},
                "referee": "D. Orsato",
            },
            "teams": {"home": {"id": 1, "name": "Qatar"}, "away": {"id": 2, "name": "Ecuador"}},
            "goals": {"home": 0, "away": 2},
            "league": {"round": "Group Stage - 1"},
        }
    ]
}

STATS_PAYLOAD = {
    "response": [
        {
            "team": {"id": 1, "name": "Qatar"},
            "statistics": [
                {"type": "Ball Possession", "value": "47%"},
                {"type": "Total Shots", "value": "5"},
            ],
        }
    ]
}

EVENTS_PAYLOAD = {
    "response": [
        {
            "time": {"elapsed": 16},
            "team": {"name": "Ecuador"},
            "player": {"name": "E. Valencia"},
            "assist": {"name": None},
            "type": "Goal",
            "detail": "Penalty",
            "comments": None,
        }
    ]
}


def test_fetch_fixtures_returns_match_data() -> None:
    with patch("src.apifootball_pipeline._fetch", return_value=FIXTURE_PAYLOAD):
        df = fetch_fixtures(season=2022)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["fixture_id"] == 855736
    assert row["home_team"] == "Qatar"
    assert row["away_team"] == "Ecuador"
    assert row["home_score"] == 0
    assert row["away_score"] == 2
    assert row["round"] == "Group Stage - 1"


def test_fetch_statistics_returns_team_stats() -> None:
    with patch("src.apifootball_pipeline._fetch", return_value=STATS_PAYLOAD):
        rows = fetch_statistics(855736)
    assert len(rows) == 2
    assert rows[0]["team_name"] == "Qatar"
    assert rows[0]["stat_type"] == "Ball Possession"
    assert rows[0]["stat_value"] == "47%"


def test_fetch_events_returns_goal_events() -> None:
    with patch("src.apifootball_pipeline._fetch", return_value=EVENTS_PAYLOAD):
        rows = fetch_events(855736)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "Goal"
    assert rows[0]["player_name"] == "E. Valencia"
