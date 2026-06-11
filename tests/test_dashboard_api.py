from fastapi.testclient import TestClient

from api.main import app


def test_health_loads_dashboard_data() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["row_counts"]["enhanced_predictions"] >= 4


def test_matches_return_chinese_team_names() -> None:
    with TestClient(app) as client:
        response = client.get("/api/matches?limit=2")

    assert response.status_code == 200
    matches = response.json()
    assert matches[0]["home_team_zh"] == "墨西哥"
    assert matches[0]["away_team_zh"] == "南非"


def test_match_scorelines_include_value_fields() -> None:
    with TestClient(app) as client:
        response = client.get("/api/matches/1/scorelines?limit=3")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 3
    assert {"scoreline", "model_probability", "value_signal"}.issubset(rows[0])


def test_group_advance_repairs_chinese_names() -> None:
    with TestClient(app) as client:
        response = client.get("/api/groups/advance?group_name=Group A")

    assert response.status_code == 200
    rows = response.json()
    mexico = next(row for row in rows if row["team_name"] == "Mexico")
    assert mexico["team_name_zh"] == "墨西哥"


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
