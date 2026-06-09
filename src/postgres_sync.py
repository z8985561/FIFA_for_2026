from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg

from .data_pipeline import prepare_research_data
from .project_paths import DATABASE_PATH, FIXTURES_PATH, MATCHES_PATH, RATINGS_PATH, TEAMS_PATH

DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_SCHEMA = "research"


POSTGRES_TABLE_COLUMNS: dict[str, list[str]] = {
    "matches": [
        "match_id",
        "match_date",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "tournament",
        "city",
        "country",
        "neutral",
        "competition_type",
        "outcome",
        "pre_match_elo_home",
        "pre_match_elo_away",
        "elo_diff",
        "expected_home_win",
        "home_rest_days",
        "away_rest_days",
        "post_match_elo_home",
        "post_match_elo_away",
    ],
    "teams": [
        "team_name",
        "first_match_date",
        "last_match_date",
        "total_matches",
    ],
    "ratings": [
        "team_name",
        "latest_match_date",
        "latest_elo",
        "matches_played",
    ],
    "fixtures_2026": [
        "match_no",
        "stage",
        "group_name",
        "date_et",
        "time_et",
        "date_bj",
        "time_bj",
        "home_team",
        "away_team",
        "venue",
        "city",
        "neutral",
    ],
}


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    schema: str = DEFAULT_SCHEMA


def load_env_file(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_postgres_config() -> PostgresConfig:
    file_env = load_env_file()

    def env_value(key: str, default: str) -> str:
        return os.getenv(key) or file_env.get(key) or default

    return PostgresConfig(
        host=env_value("POSTGRES_HOST", "127.0.0.1"),
        port=int(env_value("POSTGRES_PORT", "5432")),
        dbname=env_value("POSTGRES_DB", "fifa"),
        user=env_value("POSTGRES_USER", "fifa"),
        password=env_value("POSTGRES_PASSWORD", "fifa_dev_password"),
        schema=env_value("POSTGRES_SCHEMA", DEFAULT_SCHEMA),
    )


def ensure_processed_data() -> None:
    required_paths = [MATCHES_PATH, TEAMS_PATH, RATINGS_PATH, FIXTURES_PATH, DATABASE_PATH]
    if any(not path.exists() for path in required_paths):
        prepare_research_data()


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def qualified_table(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def postgres_schema_sql(schema: str) -> tuple[str, ...]:
    matches_table = qualified_table(schema, "matches")
    teams_table = qualified_table(schema, "teams")
    ratings_table = qualified_table(schema, "ratings")
    fixtures_table = qualified_table(schema, "fixtures_2026")
    quoted_schema = quote_identifier(schema)

    return (
        f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}",
        f"""
        CREATE TABLE IF NOT EXISTS {matches_table} (
            match_id BIGINT PRIMARY KEY,
            match_date DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            tournament TEXT NOT NULL,
            city TEXT,
            country TEXT,
            neutral BOOLEAN NOT NULL,
            competition_type TEXT NOT NULL,
            outcome TEXT NOT NULL,
            pre_match_elo_home DOUBLE PRECISION NOT NULL,
            pre_match_elo_away DOUBLE PRECISION NOT NULL,
            elo_diff DOUBLE PRECISION NOT NULL,
            expected_home_win DOUBLE PRECISION NOT NULL,
            home_rest_days DOUBLE PRECISION,
            away_rest_days DOUBLE PRECISION,
            post_match_elo_home DOUBLE PRECISION NOT NULL,
            post_match_elo_away DOUBLE PRECISION NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {teams_table} (
            team_name TEXT PRIMARY KEY,
            first_match_date DATE NOT NULL,
            last_match_date DATE NOT NULL,
            total_matches BIGINT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {ratings_table} (
            team_name TEXT PRIMARY KEY,
            latest_match_date DATE NOT NULL,
            latest_elo DOUBLE PRECISION NOT NULL,
            matches_played BIGINT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {fixtures_table} (
            match_no BIGINT PRIMARY KEY,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            time_et TEXT NOT NULL,
            date_bj DATE NOT NULL,
            time_bj TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            venue TEXT,
            city TEXT,
            neutral BOOLEAN NOT NULL
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_matches_match_date
        ON {matches_table} (match_date)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_matches_home_team
        ON {matches_table} (home_team)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_matches_away_team
        ON {matches_table} (away_team)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_fixtures_stage
        ON {fixtures_table} (stage)
        """,
    )


def create_schema_objects(connection: psycopg.Connection, schema: str) -> None:
    with connection.cursor() as cursor:
        for statement in postgres_schema_sql(schema):
            cursor.execute(statement)
    connection.commit()


def read_processed_frames() -> dict[str, pd.DataFrame]:
    return {
        "matches": pd.read_parquet(MATCHES_PATH),
        "teams": pd.read_parquet(TEAMS_PATH),
        "ratings": pd.read_parquet(RATINGS_PATH),
        "fixtures_2026": pd.read_parquet(FIXTURES_PATH),
    }


def dataframe_to_copy_buffer(frame: pd.DataFrame, columns: list[str]) -> io.StringIO:
    normalized = frame[columns].copy()
    buffer = io.StringIO()
    normalized.to_csv(
        buffer,
        index=False,
        header=False,
        na_rep="\\N",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    buffer.seek(0)
    return buffer


def truncate_tables(connection: psycopg.Connection, schema: str) -> None:
    ordered_tables = ["matches", "teams", "ratings", "fixtures_2026"]
    with connection.cursor() as cursor:
        for table in ordered_tables:
            cursor.execute(f"TRUNCATE TABLE {qualified_table(schema, table)}")
    connection.commit()


def copy_table(
    connection: psycopg.Connection,
    schema: str,
    table: str,
    frame: pd.DataFrame,
) -> None:
    columns = POSTGRES_TABLE_COLUMNS[table]
    buffer = dataframe_to_copy_buffer(frame, columns)
    column_list = ", ".join(quote_identifier(column) for column in columns)
    copy_sql = (
        f"COPY {qualified_table(schema, table)} ({column_list}) "
        "FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
    )
    with connection.cursor() as cursor:
        with cursor.copy(copy_sql) as copy:
            copy.write(buffer.read())
    connection.commit()


def sync_to_postgres(config: PostgresConfig | None = None) -> dict[str, int]:
    ensure_processed_data()
    config = config or load_postgres_config()
    frames = read_processed_frames()

    connection = psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )
    try:
        create_schema_objects(connection, config.schema)
        truncate_tables(connection, config.schema)
        for table, frame in frames.items():
            copy_table(connection, config.schema, table, frame)

        counts: dict[str, int] = {}
        with connection.cursor() as cursor:
            for table in frames:
                cursor.execute(f"SELECT COUNT(*) FROM {qualified_table(config.schema, table)}")
                counts[table] = int(cursor.fetchone()[0])
        connection.commit()
        return counts
    finally:
        connection.close()


def main() -> None:
    config = load_postgres_config()
    counts = sync_to_postgres(config)
    print(
        f"postgres://{config.user}:***@{config.host}:{config.port}/{config.dbname}"
        f" schema={config.schema}"
    )
    for table, count in counts.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()
