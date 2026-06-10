import json
from pathlib import Path

from src.odds_pipeline import (
    build_market_odds_snapshots,
    build_match_odds_features,
    discover_odds_files,
    implied_probabilities_from_odds,
)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def sample_odds_event(*, home_price: float, draw_price: float, away_price: float) -> list[dict]:
    return [
        {
            "id": "evt-1",
            "sport_key": "soccer_fifa_world_cup",
            "sport_title": "FIFA World Cup",
            "commence_time": "2026-06-11T19:00:00Z",
            "home_team": "USA",
            "away_team": "South Korea",
            "bookmakers": [
                {
                    "key": "book-a",
                    "title": "Book A",
                    "last_update": "2026-06-10T02:35:27Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "last_update": "2026-06-10T02:35:27Z",
                            "outcomes": [
                                {"name": "USA", "price": home_price},
                                {"name": "Draw", "price": draw_price},
                                {"name": "South Korea", "price": away_price},
                            ],
                        }
                    ],
                }
            ],
        }
    ]


def test_discover_odds_files_ignores_meta_files(tmp_path: Path) -> None:
    write_json(tmp_path / "odds__soccer_fifa_world_cup__one.json", [])
    write_json(tmp_path / "odds__soccer_fifa_world_cup__one.json.meta.json", {})

    files = discover_odds_files(tmp_path)

    assert [path.name for path in files] == ["odds__soccer_fifa_world_cup__one.json"]


def test_build_market_odds_snapshots_flattens_bookmakers_and_outcomes(tmp_path: Path) -> None:
    odds_path = tmp_path / "odds__soccer_fifa_world_cup__sample.json"
    write_json(odds_path, sample_odds_event(home_price=2.0, draw_price=3.5, away_price=4.0))
    write_json(
        tmp_path / "odds__soccer_fifa_world_cup__sample.json.meta.json",
        {
            "fetched_at": "2026-06-10T02:35:48.005574+00:00",
            "job": {"label": "sample-job", "markets": "h2h", "regions": "eu"},
        },
    )

    snapshots = build_market_odds_snapshots(tmp_path)

    assert len(snapshots) == 3
    assert set(snapshots["outcome_name"]) == {"United States", "Draw", "South Korea"}
    assert snapshots.loc[0, "request_label"] == "sample-job"


def test_build_match_odds_features_uses_latest_snapshot_per_bookmaker(tmp_path: Path) -> None:
    older_path = tmp_path / "odds__soccer_fifa_world_cup__older.json"
    newer_path = tmp_path / "odds__soccer_fifa_world_cup__newer.json"
    write_json(older_path, sample_odds_event(home_price=2.2, draw_price=3.4, away_price=3.8))
    write_json(newer_path, sample_odds_event(home_price=2.0, draw_price=3.5, away_price=4.0))
    write_json(
        tmp_path / "odds__soccer_fifa_world_cup__older.json.meta.json",
        {"fetched_at": "2026-06-10T02:00:00+00:00", "job": {"label": "older"}},
    )
    write_json(
        tmp_path / "odds__soccer_fifa_world_cup__newer.json.meta.json",
        {"fetched_at": "2026-06-10T03:00:00+00:00", "job": {"label": "newer"}},
    )

    snapshots = build_market_odds_snapshots(tmp_path)
    features = build_match_odds_features(snapshots)

    expected_home, expected_draw, expected_away, expected_overround = (
        implied_probabilities_from_odds(2.0, 3.5, 4.0)
    )

    assert len(features) == 1
    row = features.iloc[0]
    assert row["home_team"] == "United States"
    assert row["bookmaker_count"] == 1
    assert round(row["consensus_home_win_probability"], 8) == round(expected_home, 8)
    assert round(row["consensus_draw_probability"], 8) == round(expected_draw, 8)
    assert round(row["consensus_away_win_probability"], 8) == round(expected_away, 8)
    assert round(row["avg_market_overround"], 8) == round(expected_overround, 8)
    assert round(row["consensus_fair_probability_sum"], 8) == 1.0
    assert row["favorite_outcome"] == "home_win"
