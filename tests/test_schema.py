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
