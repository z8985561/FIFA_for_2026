from datetime import UTC, datetime

import pandas as pd

from src.score_odds_pipeline import (
    american_to_decimal,
    append_score_odds_history,
    build_score_odds_features,
    build_score_odds_snapshots,
    build_sporttery_match_id_map,
    build_sporttery_match_metadata_map,
    extract_sportsgambler_correct_score_odds,
    extract_sporttery_correct_score_odds,
    reverse_scoreline,
)


def test_american_to_decimal_converts_positive_and_negative_prices() -> None:
    assert american_to_decimal("+700") == 8.0
    assert round(american_to_decimal("-125"), 2) == 1.8


def test_extract_sportsgambler_correct_score_odds_reads_score_block() -> None:
    html = """
    <div class="correct-score-odds">
      <ul>
        <span class="mabeto-btn-no">1-0</span>
        <span class="mabeto-btn-odd">+700</span>
        <span class="mabeto-btn-no">1-1</span>
        <span class="mabeto-btn-odd">+460</span>
      </ul>
    </div>
    """

    odds = extract_sportsgambler_correct_score_odds(html)

    assert odds == [("1-0", "+700", 8.0), ("1-1", "+460", 5.6)]


def test_extract_sporttery_correct_score_odds_reads_latest_crs_row() -> None:
    payload = {
        "value": {
            "oddsHistory": {
                "crsList": [
                    {"updateDate": "2026-06-09", "updateTime": "08:52:34", "s02s00": "5.40"},
                    {
                        "updateDate": "2026-06-10",
                        "updateTime": "11:56:51",
                        "s02s00": "5.25",
                        "s-1sh": "50.00",
                    },
                ]
            }
        }
    }

    odds = extract_sporttery_correct_score_odds(payload)

    assert ("2-0", "5.25", 5.25) in odds
    assert ("胜其他", "50.00", 50.0) in odds


def test_build_score_odds_features_normalizes_listed_score_probabilities() -> None:
    snapshots = pd.DataFrame(
        {
            "match_no": [1, 1],
            "stage": ["Group Stage", "Group Stage"],
            "group_name": ["Group A", "Group A"],
            "date_et": [pd.Timestamp("2026-06-11").date()] * 2,
            "home_team": ["Mexico", "Mexico"],
            "away_team": ["South Africa", "South Africa"],
            "home_team_zh": ["墨西哥", "墨西哥"],
            "away_team_zh": ["南非", "南非"],
            "scoreline": ["1-0", "2-0"],
            "decimal_odds": [5.1, 5.3],
            "raw_implied_probability": [1 / 5.1, 1 / 5.3],
            "bookmaker_key": ["sporttery", "sportsgambler"],
            "source_name": ["中国体育彩票", "SportsGambler"],
            "fetched_at": [pd.Timestamp("2026-06-10T00:00:00Z")] * 2,
            "source_url": ["https://example.com", "https://example.com"],
            "source_match_id": ["2040162", None],
        }
    )

    features = build_score_odds_features(snapshots)

    assert len(features) == 2
    assert round(features["listed_score_fair_probability"].sum(), 8) == 1.0
    assert features.loc[0, "bookmaker_count"] == 1
    assert features.loc[0, "source_names"] == "中国体育彩票"
    assert features.loc[0, "source_match_ids"] == "2040162"


def test_append_score_odds_history_deduplicates_identical_snapshots(tmp_path) -> None:
    history_path = tmp_path / "score_odds_history.parquet"
    snapshots = pd.DataFrame(
        {
            "match_no": [1],
            "stage": ["Group Stage"],
            "group_name": ["Group A"],
            "date_et": [pd.Timestamp("2026-06-11").date()],
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "home_team_zh": ["墨西哥"],
            "away_team_zh": ["南非"],
            "scoreline": ["2-0"],
            "bookmaker_key": ["sporttery"],
            "bookmaker_title": ["中国体育彩票"],
            "american_odds": ["5.30"],
            "decimal_odds": [5.3],
            "raw_implied_probability": [1 / 5.3],
            "source_name": ["中国体育彩票"],
            "source_url": ["https://www.sporttery.cn/jc/zqdz/index.html?showType=3&mid=2040162"],
            "source_match_id": ["2040162"],
            "fetched_at": [pd.Timestamp("2026-06-11T01:00:00Z")],
        }
    )

    append_score_odds_history(snapshots, history_path=history_path)
    history = append_score_odds_history(snapshots, history_path=history_path)

    assert len(history) == 1
    assert history.loc[0, "source_match_id"] == "2040162"


def test_build_sporttery_match_id_map_filters_world_cup_rows() -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [1, 99],
            "home_team": ["Mexico", "Portugal"],
            "away_team": ["South Africa", "Nigeria"],
        }
    )
    rows = [
        {
            "matchId": 2040162,
            "leagueAllName": "世界杯",
            "homeTeamAllName": "墨西哥",
            "awayTeamAllName": "南非",
        },
        {
            "matchId": 2040189,
            "leagueAllName": "国际赛",
            "homeTeamAllName": "葡萄牙",
            "awayTeamAllName": "尼日利亚",
        },
    ]

    assert build_sporttery_match_id_map(fixtures, rows) == {1: "2040162"}


def test_sporttery_metadata_marks_reversed_home_away() -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [32],
            "home_team": ["Tunisia"],
            "away_team": ["Sweden"],
        }
    )
    rows = [
        {
            "matchId": 2040173,
            "leagueAllName": "世界杯",
            "homeTeamAllName": "瑞典",
            "awayTeamAllName": "突尼斯",
        }
    ]

    metadata = build_sporttery_match_metadata_map(fixtures, rows)

    assert metadata[32]["source_match_id"] == "2040173"
    assert metadata[32]["source_home_away_reversed"]


def test_reverse_scoreline_flips_exact_scores_and_other_buckets() -> None:
    assert reverse_scoreline("1-0") == "0-1"
    assert reverse_scoreline("胜其他") == "负其他"
    assert reverse_scoreline("平其他") == "平其他"


def test_build_score_odds_snapshots_marks_missing_sources(monkeypatch) -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [99],
            "stage": ["Group Stage"],
            "group_name": ["Group Z"],
            "date_et": [pd.Timestamp("2026-06-11")],
            "home_team": ["Unknown Home"],
            "away_team": ["Unknown Away"],
        }
    )
    monkeypatch.setattr("src.score_odds_pipeline.fetch_url", lambda url, **kwargs: "")

    snapshots, status = build_score_odds_snapshots(
        fixtures,
        fetched_at=datetime(2026, 6, 10, tzinfo=UTC),
    )

    assert snapshots.empty
    assert status.loc[0, "status"] == "missing"
    assert status.loc[0, "scoreline_count"] == 0


def test_build_score_odds_snapshots_skips_existing_sporttery_mid(monkeypatch) -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [1],
            "stage": ["Group Stage"],
            "group_name": ["Group A"],
            "date_et": [pd.Timestamp("2026-06-11")],
            "home_team": ["Mexico"],
            "away_team": ["South Africa"],
            "source_match_id": ["2040162"],
        }
    )
    monkeypatch.setattr("src.score_odds_pipeline.fetch_url", lambda url, **kwargs: "")

    snapshots, status = build_score_odds_snapshots(
        fixtures,
        fetched_at=datetime(2026, 6, 10, tzinfo=UTC),
        existing_sporttery_match_ids={"2040162"},
    )

    assert snapshots.empty
    sporttery_status = status[status["source_name"].eq("中国体育彩票")].iloc[0]
    assert sporttery_status["source_match_id"] == "2040162"
    assert sporttery_status["status"] == "skipped_existing"


def test_build_score_odds_snapshots_reverses_sporttery_scorelines(monkeypatch) -> None:
    fixtures = pd.DataFrame(
        {
            "match_no": [32],
            "stage": ["Group Stage"],
            "group_name": ["Group F"],
            "date_et": [pd.Timestamp("2026-06-14")],
            "home_team": ["Tunisia"],
            "away_team": ["Sweden"],
            "source_match_id": ["2040173"],
            "source_home_away_reversed": [True],
        }
    )
    payload = {
        "value": {
            "oddsHistory": {
                "crsList": [
                    {
                        "updateDate": "2026-06-10",
                        "updateTime": "11:56:51",
                        "s01s00": "6.00",
                    }
                ]
            }
        }
    }
    monkeypatch.setattr(
        "src.score_odds_pipeline.fetch_sporttery_fixed_bonus",
        lambda *a, **k: payload,
    )
    monkeypatch.setattr("src.score_odds_pipeline.fetch_url", lambda url, **kwargs: "")

    snapshots, _ = build_score_odds_snapshots(
        fixtures,
        fetched_at=datetime(2026, 6, 10, tzinfo=UTC),
    )

    sporttery_rows = snapshots[snapshots["source_name"].eq("中国体育彩票")]
    assert sporttery_rows.iloc[0]["scoreline"] == "0-1"
