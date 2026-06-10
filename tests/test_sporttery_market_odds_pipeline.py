from datetime import UTC, datetime

import pandas as pd

from src.sporttery_market_odds_pipeline import (
    append_sporttery_market_odds_history,
    build_sporttery_market_odds_snapshots,
    extract_sporttery_market_odds,
    normalized_goal_line,
)


def sample_fixed_bonus_payload() -> dict:
    return {
        "value": {
            "oddsHistory": {
                "hadList": [
                    {
                        "h": "1.35",
                        "d": "4.00",
                        "a": "8.00",
                        "updateDate": "2026-06-09",
                        "updateTime": "10:00:00",
                    },
                    {
                        "h": "1.30",
                        "d": "4.15",
                        "a": "8.40",
                        "updateDate": "2026-06-10",
                        "updateTime": "12:01:26",
                    },
                ],
                "hhadList": [
                    {
                        "h": "2.07",
                        "d": "3.28",
                        "a": "2.93",
                        "goalLine": "-1",
                        "updateDate": "2026-06-10",
                        "updateTime": "12:02:01",
                    }
                ],
                "ttgList": [
                    {
                        "s0": "9.50",
                        "s1": "4.40",
                        "s2": "3.05",
                        "s7": "35.00",
                        "updateDate": "2026-06-08",
                        "updateTime": "10:02:19",
                    }
                ],
                "hafuList": [
                    {
                        "hh": "1.88",
                        "hd": "21.00",
                        "aa": "16.00",
                        "updateDate": "2026-06-09",
                        "updateTime": "08:51:04",
                    }
                ],
            }
        }
    }


def test_extract_sporttery_market_odds_flattens_fixed_bonus_markets() -> None:
    odds = extract_sporttery_market_odds(sample_fixed_bonus_payload())

    had_home = next(
        row
        for row in odds
        if row["market_code"] == "HAD" and row["outcome_code"] == "home_win"
    )
    assert had_home["market_name_zh"] == "胜平负"
    assert had_home["outcome_name_zh"] == "主胜"
    assert had_home["decimal_odds"] == 1.30
    assert had_home["market_update_at"] == datetime(2026, 6, 10, 4, 1, 26, tzinfo=UTC)

    hhad_home = next(
        row
        for row in odds
        if row["market_code"] == "HHAD" and row["outcome_code"] == "home_handicap_win"
    )
    assert hhad_home["goal_line"] == -1.0

    assert any(
        row["market_code"] == "TTG" and row["outcome_code"] == "total_goals_7_plus"
        for row in odds
    )
    assert any(
        row["market_code"] == "HAFU" and row["outcome_code"] == "home_draw"
        for row in odds
    )


def test_extract_sporttery_market_odds_reverses_home_away_semantics() -> None:
    odds = extract_sporttery_market_odds(
        sample_fixed_bonus_payload(),
        source_home_away_reversed=True,
    )

    away_win = next(
        row for row in odds if row["market_code"] == "HAD" and row["outcome_code"] == "away_win"
    )
    assert away_win["source_outcome_field"] == "h"
    assert away_win["decimal_odds"] == 1.30

    hhad_away = next(
        row
        for row in odds
        if row["market_code"] == "HHAD" and row["outcome_code"] == "away_handicap_win"
    )
    assert hhad_away["source_outcome_field"] == "h"
    assert hhad_away["goal_line"] == 1.0

    hafu_away_draw = next(
        row
        for row in odds
        if row["market_code"] == "HAFU" and row["outcome_code"] == "away_draw"
    )
    assert hafu_away_draw["source_outcome_field"] == "hd"


def test_normalized_goal_line_handles_missing_and_reversed_lines() -> None:
    assert normalized_goal_line("", source_home_away_reversed=False) is None
    assert normalized_goal_line("-1", source_home_away_reversed=False) == -1.0
    assert normalized_goal_line("-1", source_home_away_reversed=True) == 1.0


def test_build_sporttery_market_odds_snapshots_uses_fixture_metadata(monkeypatch) -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [1],
            "stage": ["Group Stage"],
            "group_name": ["Group A"],
            "date_et": [pd.Timestamp("2026-06-11")],
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "source_match_id": ["2040162"],
            "source_home_away_reversed": [False],
        }
    )
    monkeypatch.setattr(
        "src.sporttery_market_odds_pipeline.fetch_sporttery_fixed_bonus",
        lambda *a, **k: sample_fixed_bonus_payload(),
    )

    snapshots = build_sporttery_market_odds_snapshots(
        fixtures,
        fetched_at=datetime(2026, 6, 10, tzinfo=UTC),
    )

    assert snapshots["source_match_id"].unique().tolist() == ["2040162"]
    assert set(snapshots["market_code"]) == {"HAD", "HHAD", "TTG", "HAFU"}
    assert "胜平负" in set(snapshots["market_name_zh"])


def test_append_sporttery_market_odds_history_deduplicates_identical_rows(tmp_path) -> None:
    history_path = tmp_path / "sporttery_market_odds_history.parquet"
    snapshots = pd.DataFrame(
        {
            "match_no": [1],
            "market_code": ["HAD"],
            "outcome_code": ["home_win"],
            "source_match_id": ["2040162"],
            "market_update_at": [pd.Timestamp("2026-06-10T04:01:26Z")],
            "fetched_at": [pd.Timestamp("2026-06-10T05:00:00Z")],
            "decimal_odds": [1.3],
        }
    )

    append_sporttery_market_odds_history(snapshots, history_path=history_path)
    history = append_sporttery_market_odds_history(snapshots, history_path=history_path)

    assert len(history) == 1
    assert history.loc[0, "decimal_odds"] == 1.3
