from src.postgres_views import view_sql


def test_view_sql_contains_expected_view_names() -> None:
    statements = view_sql("research")

    assert set(statements) == {
        "baseline_prediction_summary",
        "enhanced_prediction_summary",
        "historical_match_odds_feature_summary",
        "match_odds_feature_summary",
        "scoreline_prediction_summary",
        "odds_raw_api_response_inventory",
        "predicted_lineup_summary",
        "team_latest_snapshot",
        "match_outcome_summary",
        "world_cup_2026_known_fixtures",
        "top_rated_teams",
        "world_cup_team_profiles",
        "squad_summary",
        "rankings_snapshot",
        "team_goal_form_snapshot",
    }


def test_view_sql_targets_selected_schema() -> None:
    statements = view_sql("analytics")

    assert '"analytics".team_latest_snapshot' in statements["team_latest_snapshot"]
    assert '"analytics"."matches"' in statements["match_outcome_summary"]
    assert (
        '"analytics"."odds_raw_api_responses"'
        in statements["odds_raw_api_response_inventory"]
    )
    assert '"analytics"."predicted_lineups"' in statements["predicted_lineup_summary"]
