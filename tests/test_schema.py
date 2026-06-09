import duckdb

from src.schema import SCHEMA_SQL, apply_schema


def test_apply_schema_creates_expected_tables() -> None:
    connection = duckdb.connect(":memory:")
    try:
        apply_schema(connection)
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    finally:
        connection.close()

    assert set(SCHEMA_SQL) == tables


def test_apply_schema_can_limit_to_specific_tables() -> None:
    connection = duckdb.connect(":memory:")
    try:
        apply_schema(connection, table_names=("fifa_rankings_2026", "squads_2026"))
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    finally:
        connection.close()

    assert tables == {"fifa_rankings_2026", "squads_2026"}
