from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import psycopg

from .postgres_sync import PostgresConfig, load_env_file, qualified_table, quote_identifier

DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


@dataclass(frozen=True)
class ViewCreationResult:
    schema: str
    created_views: tuple[str, ...]


def load_postgres_view_config() -> PostgresConfig:
    file_env = load_env_file(DEFAULT_ENV_PATH)

    def env_value(key: str, default: str) -> str:
        return os.getenv(key) or file_env.get(key) or default

    return PostgresConfig(
        host=env_value("POSTGRES_HOST", "127.0.0.1"),
        port=int(env_value("POSTGRES_PORT", "5432")),
        dbname=env_value("POSTGRES_DB", "fifa"),
        user=env_value("POSTGRES_USER", "fifa"),
        password=env_value("POSTGRES_PASSWORD", "fifa_dev_password"),
        schema=env_value("POSTGRES_SCHEMA", "research"),
    )


def view_sql(schema: str) -> dict[str, str]:
    matches = qualified_table(schema, "matches")
    ratings = qualified_table(schema, "ratings")
    teams = qualified_table(schema, "teams")
    fixtures = qualified_table(schema, "fixtures_2026")
    predictions = qualified_table(schema, "baseline_predictions")
    qs = quote_identifier(schema)

    return {
        "team_latest_snapshot": f"""
            CREATE OR REPLACE VIEW {qs}.team_latest_snapshot AS
            SELECT
                t.team_name,
                t.first_match_date,
                t.last_match_date,
                t.total_matches,
                r.latest_match_date,
                r.latest_elo,
                r.matches_played
            FROM {teams} AS t
            LEFT JOIN {ratings} AS r
                ON t.team_name = r.team_name
        """,
        "match_outcome_summary": f"""
            CREATE OR REPLACE VIEW {qs}.match_outcome_summary AS
            SELECT
                home_team AS team_name,
                COUNT(*) AS home_matches,
                AVG(CASE WHEN outcome = 'home_win' THEN 1.0 ELSE 0.0 END) AS home_win_rate,
                AVG(home_score) AS avg_home_goals,
                AVG(away_score) AS avg_home_goals_conceded
            FROM {matches}
            GROUP BY home_team
        """,
        "world_cup_2026_known_fixtures": f"""
            CREATE OR REPLACE VIEW {qs}.world_cup_2026_known_fixtures AS
            SELECT *
            FROM {fixtures}
            WHERE home_team <> 'TBD'
              AND away_team <> 'TBD'
        """,
        "top_rated_teams": f"""
            CREATE OR REPLACE VIEW {qs}.top_rated_teams AS
            SELECT
                team_name,
                latest_match_date,
                latest_elo,
                matches_played
            FROM {ratings}
            ORDER BY latest_elo DESC, team_name ASC
        """,
        "baseline_prediction_summary": f"""
            CREATE OR REPLACE VIEW {qs}.baseline_prediction_summary AS
            SELECT
                match_no,
                stage,
                group_name,
                date_et,
                home_team,
                away_team,
                ROUND(home_win_probability::numeric, 4) AS home_win_probability,
                ROUND(draw_probability::numeric, 4) AS draw_probability,
                ROUND(away_win_probability::numeric, 4) AS away_win_probability,
                predicted_outcome
            FROM {predictions}
        """,
    }


def create_views(config: PostgresConfig | None = None) -> ViewCreationResult:
    config = config or load_postgres_view_config()
    statements = view_sql(config.schema)

    connection = psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )
    try:
        with connection.cursor() as cursor:
            for statement in statements.values():
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()

    return ViewCreationResult(
        schema=config.schema,
        created_views=tuple(statements.keys()),
    )


def main() -> None:
    result = create_views()
    print(f"schema: {result.schema}")
    for view_name in result.created_views:
        print(f"view: {view_name}")


if __name__ == "__main__":
    main()
