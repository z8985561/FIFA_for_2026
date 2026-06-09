from pathlib import Path

from src.postgres_sync import load_env_file, postgres_schema_sql, qualified_table


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
    assert any('"analytics"."match_feature_store_2026"' in statement for statement in statements)
    assert any(
        '"analytics"."historical_match_feature_store"' in statement for statement in statements
    )
    assert any('"analytics"."enhanced_predictions"' in statement for statement in statements)


def test_qualified_table_quotes_schema_and_table() -> None:
    assert qualified_table("research", "matches") == '"research"."matches"'
