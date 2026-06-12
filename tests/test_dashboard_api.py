from fastapi.testclient import TestClient

from api.main import app


def test_health_loads_dashboard_data() -> None:
    with TestClient(app) as client:
      response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["row_counts"]["enhanced_predictions"] >= 4


def test_metadata_exposes_snapshot_times_and_compliance_note() -> None:
    with TestClient(app) as client:
      response = client.get("/api/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "dashboard-mvp-0.1"
    assert payload["latest_score_odds_fetched_at"] is not None
    assert "真实下单" in payload["compliance_note"]


def test_matches_return_chinese_team_names() -> None:
    with TestClient(app) as client:
      response = client.get("/api/matches?limit=2")

    assert response.status_code == 200
    matches = response.json()
    assert matches[0]["home_team_zh"] == "墨西哥"
    assert matches[0]["away_team_zh"] == "南非"


def test_schedule_returns_full_fixture_list_with_knockout_placeholders() -> None:
    with TestClient(app) as client:
      response = client.get("/api/schedule")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 104
    assert rows[0]["home_team_zh"] == "墨西哥"
    assert rows[0]["completed"] is True
    assert rows[0]["actual_home_score"] == 2
    assert rows[0]["actual_away_score"] == 0
    assert rows[-1]["stage"] == "Final"
    assert rows[-1]["home_team_zh"] == "待定"


def test_data_quality_returns_high_quality_seeded_match_and_low_quality_final() -> None:
    with TestClient(app) as client:
      response = client.get("/api/data-quality")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 104

    match_one = next(row for row in rows if row["match_no"] == 1)
    assert match_one["home_team_zh"] == "墨西哥"
    assert match_one["completeness_level"] == "High"
    assert match_one["completeness_score"] >= 90
    assert match_one["missing_items"] == []

    final = next(row for row in rows if row["match_no"] == 104)
    assert final["stage"] == "Final"
    assert final["home_team_zh"] == "待定"
    assert final["completeness_level"] == "Low"
    assert "missing_prediction" in final["missing_items"]
    assert "missing_scoreline_model" in final["missing_items"]


def test_match_scorelines_include_value_fields() -> None:
    with TestClient(app) as client:
      response = client.get("/api/matches/1/scorelines?limit=3")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 3
    assert {"scoreline", "model_probability", "value_signal"}.issubset(rows[0])
    assert rows[0]["home_team_zh"] == "墨西哥"
    assert rows[0]["away_team_zh"] == "南非"


def test_group_advance_repairs_chinese_names_and_live_standings() -> None:
    with TestClient(app) as client:
      response = client.get("/api/groups/advance?group_name=Group A")

    assert response.status_code == 200
    rows = response.json()

    mexico = next(row for row in rows if row["team_name"] == "Mexico")
    assert mexico["team_name_zh"] == "墨西哥"
    assert mexico["points"] == 3
    assert mexico["goal_difference"] == 2
    assert mexico["standing_rank"] == 1

    south_korea = next(row for row in rows if row["team_name"] == "South Korea")
    assert south_korea["points"] == 3
    assert south_korea["standing_rank"] == 2

    south_africa = next(row for row in rows if row["team_name"] == "South Africa")
    assert south_africa["points"] == 0
    assert south_africa["standing_rank"] == 4


def test_simulator_settles_two_by_one() -> None:
    request = {
        "budget": 20,
        "stake_per_combination": 2,
        "bet_type": "2x1",
        "selections": [
            {"match_no": 1, "scoreline": "2-0"},
            {"match_no": 2, "scoreline": "1-1"},
            {"match_no": 19, "scoreline": "1-1"},
        ],
    }
    with TestClient(app) as client:
      response = client.post("/api/simulator/settle", json=request)

    assert response.status_code == 200
    payload = response.json()
    assert payload["combination_count"] == 3
    assert payload["total_stake"] == 6
    assert payload["risk_rating"] in {"Low", "Medium", "High", "Extreme"}
