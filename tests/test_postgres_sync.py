from pathlib import Path

from src.postgres_sync import (
    build_raw_odds_api_response_frame,
    load_env_file,
    postgres_schema_sql,
    qualified_table,
)


def test_load_env_file_parses_simple_key_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "POSTGRES_DB=fifa\nPOSTGRES_USER=fifa_user\n# comment\nPOSTGRES_PORT=5432\n",
        encoding="utf-8",
    )

    values = load_env_file(env_path)

    assert values["POSTGRES_DB"] == "fifa"
    assert values["POSTGRES_USER"] == "fifa_user"
    assert values["POSTGRES_PORT"] == "5432"


def test_postgres_schema_sql_uses_requested_schema() -> None:
    statements = postgres_schema_sql("analytics")

    assert any('"analytics"."matches"' in statement for statement in statements)
    assert any('CREATE SCHEMA IF NOT EXISTS "analytics"' in statement for statement in statements)
    assert any('"analytics"."world_cup_teams_2026"' in statement for statement in statements)
    assert any('"analytics"."team_goal_form_features"' in statement for statement in statements)
    assert any('"analytics"."match_feature_store_2026"' in statement for statement in statements)
    assert any(
        '"analytics"."historical_match_feature_store"' in statement for statement in statements
    )
    assert any('"analytics"."enhanced_predictions"' in statement for statement in statements)
    assert any('"analytics"."scoreline_analysis"' in statement for statement in statements)
    assert any('"analytics"."odds_raw_api_responses"' in statement for statement in statements)
    assert any('"analytics"."market_odds_snapshots"' in statement for statement in statements)
    assert any('"analytics"."match_odds_features"' in statement for statement in statements)
    assert any(
        '"analytics"."historical_market_odds_snapshots"' in statement
        for statement in statements
    )
    assert any(
        '"analytics"."historical_match_odds_features"' in statement
        for statement in statements
    )
    enhanced_prediction_statement = next(
        statement for statement in statements if '"analytics"."enhanced_predictions"' in statement
    )
    assert "blended_home_win_probability" in enhanced_prediction_statement
    assert "consensus_home_win_probability" in enhanced_prediction_statement
    raw_odds_statement = next(
        statement for statement in statements if '"analytics"."odds_raw_api_responses"' in statement
    )
    assert "payload_json JSONB NOT NULL" in raw_odds_statement


def test_qualified_table_quotes_schema_and_table() -> None:
    assert qualified_table("research", "matches") == '"research"."matches"'


def test_build_raw_odds_api_response_frame_reads_payload_and_metadata(tmp_path: Path) -> None:
    payload_path = tmp_path / "odds__soccer_fifa_world_cup__sample.json"
    payload_path.write_text('[{"id":"evt-1"}]', encoding="utf-8")
    metadata_path = tmp_path / "odds__soccer_fifa_world_cup__sample.json.meta.json"
    metadata_path.write_text(
        '{"fetched_at":"2026-06-10T02:35:48Z"}',
        encoding="utf-8",
    )

    frame = build_raw_odds_api_response_frame(tmp_path)

    assert len(frame) == 1
    assert frame.loc[0, "source_file"] == payload_path.name
    assert frame.loc[0, "payload_type"] == "odds"
    assert frame.loc[0, "sport_key"] == "soccer_fifa_world_cup"
    assert frame.loc[0, "payload_json"] == '[{"id":"evt-1"}]'
    assert "fetched_at" in frame.loc[0, "metadata_json"]
