from __future__ import annotations

from collections.abc import Iterable

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
    "fifa_rankings_2026": """
        CREATE OR REPLACE TABLE fifa_rankings_2026 (
            fifa_rank INTEGER,
            team_name VARCHAR,
            ranking_source VARCHAR,
            ranking_date DATE,
            points DOUBLE
        )
    """,
    "squads_2026": """
        CREATE OR REPLACE TABLE squads_2026 (
            team_id VARCHAR,
            team_name VARCHAR,
            group_name VARCHAR,
            shirt_number INTEGER,
            position VARCHAR,
            player_name VARCHAR,
            captain BOOLEAN,
            date_of_birth DATE,
            age INTEGER,
            caps BIGINT,
            goals BIGINT,
            club VARCHAR,
            source_url VARCHAR
        )
    """,
    "world_cup_teams_2026": """
        CREATE OR REPLACE TABLE world_cup_teams_2026 (
            team_id VARCHAR,
            team_name VARCHAR,
            group_name VARCHAR,
            confederation VARCHAR,
            fifa_rank INTEGER,
            ranking_source VARCHAR,
            ranking_date DATE,
            latest_elo DOUBLE,
            latest_match_date DATE,
            matches_played BIGINT,
            first_match_date DATE,
            last_match_date DATE,
            total_matches BIGINT,
            squad_size BIGINT,
            squad_average_age DOUBLE,
            squad_total_caps BIGINT
        )
    """,
    "match_feature_store_2026": """
        CREATE OR REPLACE TABLE match_feature_store_2026 (
            match_no BIGINT,
            stage VARCHAR,
            group_name VARCHAR,
            date_et DATE,
            home_team VARCHAR,
            away_team VARCHAR,
            home_confederation VARCHAR,
            away_confederation VARCHAR,
            same_confederation BOOLEAN,
            home_fifa_rank INTEGER,
            away_fifa_rank INTEGER,
            home_rank_advantage INTEGER,
            home_latest_elo DOUBLE,
            away_latest_elo DOUBLE,
            elo_diff DOUBLE,
            expected_home_win DOUBLE,
            home_squad_size BIGINT,
            away_squad_size BIGINT,
            squad_size_diff BIGINT,
            home_squad_average_age DOUBLE,
            away_squad_average_age DOUBLE,
            squad_average_age_diff DOUBLE,
            home_squad_total_caps BIGINT,
            away_squad_total_caps BIGINT,
            squad_total_caps_diff BIGINT,
            home_matches_played BIGINT,
            away_matches_played BIGINT,
            matches_played_diff BIGINT,
            group_difficulty_rank BIGINT,
            group_avg_elo DOUBLE,
            group_avg_fifa_rank DOUBLE,
            group_elo_spread DOUBLE,
            neutral BOOLEAN
        )
    """,
}


def apply_schema(
    connection: DuckDBPyConnection,
    table_names: Iterable[str] | None = None,
) -> None:
    names = tuple(table_names) if table_names is not None else tuple(SCHEMA_SQL)
    for table_name in names:
        statement = SCHEMA_SQL[table_name]
        connection.execute(statement)
