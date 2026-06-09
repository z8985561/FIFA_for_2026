from __future__ import annotations

from duckdb import DuckDBPyConnection

SCHEMA_SQL: dict[str, str] = {
    "matches": """
        CREATE OR REPLACE TABLE matches (
            match_id BIGINT,
            match_date DATE,
            home_team VARCHAR,
            away_team VARCHAR,
            home_score INTEGER,
            away_score INTEGER,
            tournament VARCHAR,
            city VARCHAR,
            country VARCHAR,
            neutral BOOLEAN,
            competition_type VARCHAR,
            outcome VARCHAR,
            pre_match_elo_home DOUBLE,
            pre_match_elo_away DOUBLE,
            elo_diff DOUBLE,
            expected_home_win DOUBLE,
            home_rest_days DOUBLE,
            away_rest_days DOUBLE,
            post_match_elo_home DOUBLE,
            post_match_elo_away DOUBLE
        )
    """,
    "teams": """
        CREATE OR REPLACE TABLE teams (
            team_name VARCHAR,
            first_match_date DATE,
            last_match_date DATE,
            total_matches BIGINT
        )
    """,
    "ratings": """
        CREATE OR REPLACE TABLE ratings (
            team_name VARCHAR,
            latest_match_date DATE,
            latest_elo DOUBLE,
            matches_played BIGINT
        )
    """,
    "fixtures_2026": """
        CREATE OR REPLACE TABLE fixtures_2026 (
            match_no BIGINT,
            stage VARCHAR,
            group_name VARCHAR,
            date_et DATE,
            time_et VARCHAR,
            date_bj DATE,
            time_bj VARCHAR,
            home_team VARCHAR,
            away_team VARCHAR,
            venue VARCHAR,
            city VARCHAR,
            neutral BOOLEAN
        )
    """,
}


def apply_schema(connection: DuckDBPyConnection) -> None:
    for statement in SCHEMA_SQL.values():
        connection.execute(statement)
