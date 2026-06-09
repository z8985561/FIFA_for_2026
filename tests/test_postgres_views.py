from src.postgres_views import view_sql


def test_view_sql_contains_expected_view_names() -> None:
    statements = view_sql("research")

    assert set(statements) == {
        "baseline_prediction_summary",
        "team_latest_snapshot",
        "match_outcome_summary",
        "world_cup_2026_known_fixtures",
        "top_rated_teams",
    }


def test_view_sql_targets_selected_schema() -> None:
    statements = view_sql("analytics")

    assert '"analytics".team_latest_snapshot' in statements["team_latest_snapshot"]
    assert '"analytics"."matches"' in statements["match_outcome_summary"]
