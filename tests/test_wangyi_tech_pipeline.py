from unittest.mock import patch

import pandas as pd

from src.wangyi_tech_pipeline import (
    build_players_frame,
    build_tech_frame,
    fetch_finished_schedule,
)

FINISHED_MOCK = [
    {
        "mid": 4459820,
        "home": "墨西哥",
        "away": "南非",
        "homeScore": 2,
        "awayScore": 0,
        "groupName": "A组",
        "date": 1781204400000,
    },
]

TECH_DETAIL_MOCK = {
    "data": {
        "mid": 4459820,
        "homeCoach": "哈维尔·阿吉雷",
        "awayCoach": "雨果·布罗斯",
        "homeTeamTech": {
            "team": "墨西哥",
            "possessionPercentage": 60,
            "totalScoringAtt": 11,
            "ontargetScoringAtt": 4,
            "wonCorners": 3,
            "totalAttackingPass": 120,
            "totalYelCard": 1,
            "totalRedCard": 1,
            "goals": 2,
        },
        "awayTeamTech": {
            "team": "南非",
            "possessionPercentage": 40,
            "totalScoringAtt": 3,
            "ontargetScoringAtt": 2,
            "wonCorners": 1,
            "totalAttackingPass": 58,
            "totalYelCard": 2,
            "totalRedCard": 2,
            "goals": 0,
        },
        "homeTeamSeasonTech": {
            "goals": 2,
            "goalsConceded": 0,
            "totalScoringAtt": 11,
            "ontargetScoringAtt": 4,
            "fouls": 10,
            "totalYelCard": 1,
            "totalRedCard": 1,
        },
        "awayTeamSeasonTech": {
            "goals": 0,
            "goalsConceded": 2,
            "totalScoringAtt": 3,
            "ontargetScoringAtt": 2,
            "fouls": 15,
            "totalYelCard": 2,
            "totalRedCard": 2,
        },
        "players": [
            {
                "player": "R.希门尼斯",
                "playerId": 12345,
                "position": "前锋",
                "side": 1,
                "isStarting": 1,
                "jerseyNum": 9,
                "event": [
                    {"type": "goal", "time": 66, "side": 1},
                    {"type": "substitute", "time": 75, "side": 1},
                ],
            },
            {
                "player": "蒙特斯",
                "playerId": 12346,
                "position": "后卫",
                "side": 1,
                "isStarting": 1,
                "jerseyNum": 4,
                "event": [{"type": "red", "time": 91, "side": 1}],
            },
            {
                "player": "阿波利斯",
                "playerId": 67890,
                "position": "前锋",
                "side": 2,
                "isStarting": 1,
                "jerseyNum": 11,
                "event": [],
            },
        ],
    }
}


def test_fetch_finished_schedule_returns_list() -> None:
    with patch(
        "src.wangyi_tech_pipeline._fetch_json",
        return_value={"data": {"finishScheduleList": FINISHED_MOCK}},
    ):
        result = fetch_finished_schedule()
    assert len(result) == 1
    assert result[0]["mid"] == 4459820
    assert result[0]["home"] == "墨西哥"


def test_build_tech_frame_extracts_team_stats() -> None:
    with patch(
        "src.wangyi_tech_pipeline.fetch_tech_detail",
        return_value=TECH_DETAIL_MOCK["data"],
    ):
        df = build_tech_frame(FINISHED_MOCK)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["home_team"] == "墨西哥"
    assert row["away_team"] == "南非"
    assert row["home_score"] == 2
    assert row["away_score"] == 0
    assert row["group_name"] == "A组"
    assert row["home_coach"] == "哈维尔·阿吉雷"
    assert row["away_coach"] == "雨果·布罗斯"
    assert row["home_possession"] == 60
    assert row["away_possession"] == 40
    assert row["home_shots"] == 11
    assert row["away_shots"] == 3
    assert row["home_shots_on_target"] == 4
    assert row["away_shots_on_target"] == 2
    assert row["home_corners"] == 3
    assert row["away_corners"] == 1
    assert row["home_red_cards"] == 1
    assert row["away_red_cards"] == 2
    assert row["home_season_goals"] == 2
    assert row["away_season_fouls"] == 15
    assert row["match_date"] is not None
    assert row["fetched_at"] is not None


def test_build_players_frame_extracts_events() -> None:
    with patch(
        "src.wangyi_tech_pipeline.fetch_tech_detail",
        return_value=TECH_DETAIL_MOCK["data"],
    ):
        df = build_players_frame(FINISHED_MOCK)

    assert len(df) == 3

    jimenez = df[df["player_name"] == "R.希门尼斯"].iloc[0]
    assert jimenez["mid"] == 4459820
    assert jimenez["position"] == "前锋"
    assert jimenez["side"] == 1
    assert jimenez["is_starting"] == 1
    assert bool(jimenez["has_goal"]) is True
    assert bool(jimenez["has_yellow"]) is False
    assert bool(jimenez["has_red"]) is False
    assert jimenez["event_count"] == 1

    montes = df[df["player_name"] == "蒙特斯"].iloc[0]
    assert bool(montes["has_red"]) is True
    assert bool(montes["has_goal"]) is False

    apolis = df[df["player_name"] == "阿波利斯"].iloc[0]
    assert apolis["event_count"] == 0
    assert apolis["events_json"] is None


def test_build_players_frame_columns_match_schema() -> None:
    with patch(
        "src.wangyi_tech_pipeline.fetch_tech_detail",
        return_value=TECH_DETAIL_MOCK["data"],
    ):
        df = build_players_frame(FINISHED_MOCK)

    expected = {
        "mid",
        "player_name",
        "player_id",
        "position",
        "side",
        "is_starting",
        "jersey_num",
        "events_json",
        "event_count",
        "has_goal",
        "has_yellow",
        "has_red",
    }
    assert set(df.columns) == expected


def test_build_tech_frame_handles_missing_season_stats() -> None:
    detail_no_season = {**TECH_DETAIL_MOCK["data"]}
    del detail_no_season["homeTeamSeasonTech"]
    del detail_no_season["awayTeamSeasonTech"]

    with patch(
        "src.wangyi_tech_pipeline.fetch_tech_detail",
        return_value=detail_no_season,
    ):
        df = build_tech_frame(FINISHED_MOCK)

    row = df.iloc[0]
    assert row["home_season_goals"] == 0
    assert row["away_season_goals"] == 0
