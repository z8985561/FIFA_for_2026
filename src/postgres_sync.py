from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg

from .data_pipeline import prepare_research_data
from .enhanced_features import enhanced_feature_columns
from .enhanced_model import prepare_enhanced_outputs
from .feature_store import prepare_match_feature_store
from .project_paths import (
    BASELINE_PREDICTIONS_PATH,
    DATABASE_PATH,
    ENHANCED_PREDICTIONS_PATH,
    FIFA_RANKINGS_PATH,
    FIXTURES_PATH,
    HISTORICAL_MATCH_FEATURE_STORE_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    MATCHES_PATH,
    RATINGS_PATH,
    SQUADS_2026_PATH,
    TEAMS_PATH,
    WORLD_CUP_TEAMS_2026_PATH,
)
from .world_cup_identity import prepare_world_cup_identity_data

DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_SCHEMA = "research"

HISTORICAL_FEATURE_STORE_ID_COLUMNS = [
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "competition_type",
    "outcome",
]

ENHANCED_PREDICTION_COLUMNS = [
    "match_no",
    "stage",
    "group_name",
    "date_et",
    "home_team",
    "away_team",
    "home_latest_elo",
    "away_latest_elo",
    "elo_diff",
    "expected_home_win",
    "home_rest_days",
    "away_rest_days",
    "rest_days_diff",
    "points_per_match_diff_last_5",
    "goal_diff_per_match_diff_last_5",
    "win_rate_diff_last_10",
    "away_win_probability",
    "draw_probability",
    "home_win_probability",
    "predicted_outcome",
]


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
    "baseline_predictions": [
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
        "away_win_probability",
        "draw_probability",
        "home_win_probability",
        "predicted_outcome",
    ],
    "fifa_rankings_2026": [
        "fifa_rank",
        "team_name",
        "ranking_source",
        "ranking_date",
        "points",
    ],
    "squads_2026": [
        "team_id",
        "team_name",
        "group_name",
        "shirt_number",
        "position",
        "player_name",
        "captain",
        "date_of_birth",
        "age",
        "caps",
        "goals",
        "club",
        "source_url",
    ],
    "world_cup_teams_2026": [
        "team_id",
        "team_name",
        "group_name",
        "confederation",
        "fifa_rank",
        "ranking_source",
        "ranking_date",
        "latest_elo",
        "latest_match_date",
        "matches_played",
        "first_match_date",
        "last_match_date",
        "total_matches",
        "squad_size",
        "squad_average_age",
        "squad_total_caps",
    ],
    "match_feature_store_2026": [
        "match_no",
        "stage",
        "group_name",
        "date_et",
        "home_team",
        "away_team",
        "home_confederation",
        "away_confederation",
        "same_confederation",
        "home_fifa_rank",
        "away_fifa_rank",
        "home_rank_advantage",
        "home_latest_elo",
        "away_latest_elo",
        "elo_diff",
        "expected_home_win",
        "home_squad_size",
        "away_squad_size",
        "squad_size_diff",
        "home_squad_average_age",
        "away_squad_average_age",
        "squad_average_age_diff",
        "home_squad_total_caps",
        "away_squad_total_caps",
        "squad_total_caps_diff",
        "home_matches_played",
        "away_matches_played",
        "matches_played_diff",
        "group_difficulty_rank",
        "group_avg_elo",
        "group_avg_fifa_rank",
        "group_elo_spread",
        "neutral",
    ],
    "historical_match_feature_store": [
        *HISTORICAL_FEATURE_STORE_ID_COLUMNS,
        *enhanced_feature_columns(),
    ],
    "enhanced_predictions": ENHANCED_PREDICTION_COLUMNS,
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
    required_paths = [
        MATCHES_PATH,
        TEAMS_PATH,
        RATINGS_PATH,
        FIXTURES_PATH,
        DATABASE_PATH,
        FIFA_RANKINGS_PATH,
        SQUADS_2026_PATH,
        WORLD_CUP_TEAMS_2026_PATH,
        MATCH_FEATURE_STORE_2026_PATH,
        HISTORICAL_MATCH_FEATURE_STORE_PATH,
        ENHANCED_PREDICTIONS_PATH,
    ]
    if any(not path.exists() for path in required_paths):
        prepare_research_data()
        prepare_world_cup_identity_data()
        prepare_match_feature_store()
        prepare_enhanced_outputs()


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def qualified_table(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def postgres_schema_sql(schema: str) -> tuple[str, ...]:
    matches_table = qualified_table(schema, "matches")
    teams_table = qualified_table(schema, "teams")
    ratings_table = qualified_table(schema, "ratings")
    fixtures_table = qualified_table(schema, "fixtures_2026")
    predictions_table = qualified_table(schema, "baseline_predictions")
    rankings_table = qualified_table(schema, "fifa_rankings_2026")
    squads_table = qualified_table(schema, "squads_2026")
    world_cup_teams_table = qualified_table(schema, "world_cup_teams_2026")
    match_feature_store_table = qualified_table(schema, "match_feature_store_2026")
    historical_feature_store_table = qualified_table(schema, "historical_match_feature_store")
    enhanced_predictions_table = qualified_table(schema, "enhanced_predictions")
    quoted_schema = quote_identifier(schema)
    historical_feature_columns_sql = ",\n            ".join(
        f"{quote_identifier(column)} DOUBLE PRECISION NOT NULL"
        for column in enhanced_feature_columns()
    )

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
        CREATE TABLE IF NOT EXISTS {predictions_table} (
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
            away_win_probability DOUBLE PRECISION NOT NULL,
            draw_probability DOUBLE PRECISION NOT NULL,
            home_win_probability DOUBLE PRECISION NOT NULL,
            predicted_outcome TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {rankings_table} (
            fifa_rank INTEGER NOT NULL,
            team_name TEXT PRIMARY KEY,
            ranking_source TEXT NOT NULL,
            ranking_date DATE NOT NULL,
            points DOUBLE PRECISION
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {squads_table} (
            team_id TEXT NOT NULL,
            team_name TEXT NOT NULL,
            group_name TEXT NOT NULL,
            shirt_number INTEGER NOT NULL,
            position TEXT NOT NULL,
            player_name TEXT NOT NULL,
            captain BOOLEAN NOT NULL,
            date_of_birth DATE NOT NULL,
            age INTEGER NOT NULL,
            caps BIGINT NOT NULL,
            goals BIGINT NOT NULL,
            club TEXT NOT NULL,
            source_url TEXT NOT NULL,
            PRIMARY KEY (team_name, shirt_number)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {world_cup_teams_table} (
            team_id TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            group_name TEXT NOT NULL,
            confederation TEXT,
            fifa_rank INTEGER,
            ranking_source TEXT,
            ranking_date DATE,
            latest_elo DOUBLE PRECISION,
            latest_match_date DATE,
            matches_played BIGINT,
            first_match_date DATE,
            last_match_date DATE,
            total_matches BIGINT,
            squad_size BIGINT,
            squad_average_age DOUBLE PRECISION,
            squad_total_caps BIGINT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {match_feature_store_table} (
            match_no BIGINT PRIMARY KEY,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_confederation TEXT,
            away_confederation TEXT,
            same_confederation BOOLEAN NOT NULL,
            home_fifa_rank INTEGER,
            away_fifa_rank INTEGER,
            home_rank_advantage INTEGER,
            home_latest_elo DOUBLE PRECISION,
            away_latest_elo DOUBLE PRECISION,
            elo_diff DOUBLE PRECISION,
            expected_home_win DOUBLE PRECISION,
            home_squad_size BIGINT,
            away_squad_size BIGINT,
            squad_size_diff BIGINT,
            home_squad_average_age DOUBLE PRECISION,
            away_squad_average_age DOUBLE PRECISION,
            squad_average_age_diff DOUBLE PRECISION,
            home_squad_total_caps BIGINT,
            away_squad_total_caps BIGINT,
            squad_total_caps_diff BIGINT,
            home_matches_played BIGINT,
            away_matches_played BIGINT,
            matches_played_diff BIGINT,
            group_difficulty_rank BIGINT,
            group_avg_elo DOUBLE PRECISION,
            group_avg_fifa_rank DOUBLE PRECISION,
            group_elo_spread DOUBLE PRECISION,
            neutral BOOLEAN NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {historical_feature_store_table} (
            match_id BIGINT PRIMARY KEY,
            match_date DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            competition_type TEXT NOT NULL,
            outcome TEXT NOT NULL,
            {historical_feature_columns_sql}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {enhanced_predictions_table} (
            match_no BIGINT PRIMARY KEY,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_latest_elo DOUBLE PRECISION,
            away_latest_elo DOUBLE PRECISION,
            elo_diff DOUBLE PRECISION,
            expected_home_win DOUBLE PRECISION,
            home_rest_days DOUBLE PRECISION,
            away_rest_days DOUBLE PRECISION,
            rest_days_diff DOUBLE PRECISION,
            points_per_match_diff_last_5 DOUBLE PRECISION,
            goal_diff_per_match_diff_last_5 DOUBLE PRECISION,
            win_rate_diff_last_10 DOUBLE PRECISION,
            away_win_probability DOUBLE PRECISION NOT NULL,
            draw_probability DOUBLE PRECISION NOT NULL,
            home_win_probability DOUBLE PRECISION NOT NULL,
            predicted_outcome TEXT NOT NULL
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
        f"""
        CREATE INDEX IF NOT EXISTS idx_predictions_stage
        ON {predictions_table} (stage)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_rankings_rank
        ON {rankings_table} (fifa_rank)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_squads_team
        ON {squads_table} (team_name)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_world_cup_teams_group
        ON {world_cup_teams_table} (group_name)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_match_feature_store_group
        ON {match_feature_store_table} (group_name)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_historical_feature_store_match_date
        ON {historical_feature_store_table} (match_date)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_enhanced_predictions_group
        ON {enhanced_predictions_table} (group_name)
        """,
    )


def create_schema_objects(connection: psycopg.Connection, schema: str) -> None:
    with connection.cursor() as cursor:
        for statement in postgres_schema_sql(schema):
            cursor.execute(statement)
    connection.commit()


def read_processed_frames() -> dict[str, pd.DataFrame]:
    baseline_predictions = (
        pd.read_csv(BASELINE_PREDICTIONS_PATH)
        if BASELINE_PREDICTIONS_PATH.exists()
        else pd.DataFrame()
    )
    return {
        "matches": pd.read_parquet(MATCHES_PATH),
        "teams": pd.read_parquet(TEAMS_PATH),
        "ratings": pd.read_parquet(RATINGS_PATH),
        "fixtures_2026": pd.read_parquet(FIXTURES_PATH),
        "baseline_predictions": baseline_predictions,
        "fifa_rankings_2026": pd.read_parquet(FIFA_RANKINGS_PATH),
        "squads_2026": pd.read_parquet(SQUADS_2026_PATH),
        "world_cup_teams_2026": pd.read_parquet(WORLD_CUP_TEAMS_2026_PATH),
        "match_feature_store_2026": pd.read_parquet(MATCH_FEATURE_STORE_2026_PATH),
        "historical_match_feature_store": pd.read_parquet(HISTORICAL_MATCH_FEATURE_STORE_PATH),
        "enhanced_predictions": (
            pd.read_csv(ENHANCED_PREDICTIONS_PATH)
            if ENHANCED_PREDICTIONS_PATH.exists()
            else pd.DataFrame()
        ),
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
    ordered_tables = [
        "matches",
        "teams",
        "ratings",
        "fixtures_2026",
        "baseline_predictions",
        "fifa_rankings_2026",
        "squads_2026",
        "world_cup_teams_2026",
        "match_feature_store_2026",
        "historical_match_feature_store",
        "enhanced_predictions",
    ]
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
            if frame.empty:
                continue
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
