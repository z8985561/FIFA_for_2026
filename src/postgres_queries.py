from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import psycopg

from .postgres_views import load_postgres_view_config


def qualified_name(schema: str, relation: str) -> str:
    return f'"{schema}"."{relation}"'


def run_query(
    sql: str, params: tuple[Any, ...] | None = None
) -> tuple[list[str], list[tuple[Any, ...]]]:
    config = load_postgres_view_config()
    connection = psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            columns = [desc.name for desc in cursor.description]
        connection.commit()
        return columns, rows
    finally:
        connection.close()


def print_table(columns: list[str], rows: list[tuple[Any, ...]]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(columns)
    writer.writerows(rows)


def write_output(path: str, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def query_top_rated(limit: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            team_name,
            latest_match_date,
            ROUND(latest_elo::numeric, 2) AS latest_elo,
            matches_played
        FROM {qualified_name(schema, "top_rated_teams")}
        LIMIT %s
    """
    return run_query(sql, (limit,))


def query_team_history(team: str, limit: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            match_date,
            home_team,
            away_team,
            home_score,
            away_score,
            tournament,
            outcome,
            ROUND(pre_match_elo_home::numeric, 2) AS pre_match_elo_home,
            ROUND(pre_match_elo_away::numeric, 2) AS pre_match_elo_away
        FROM {qualified_name(schema, "matches")}
        WHERE home_team = %s OR away_team = %s
        ORDER BY match_date DESC
        LIMIT %s
    """
    return run_query(sql, (team, team, limit))


def query_fixtures(
    stage: str | None,
    group_name: str | None,
    limit: int,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    clauses: list[str] = []
    params: list[Any] = []

    if stage:
        clauses.append("stage = %s")
        params.append(stage)
    if group_name:
        clauses.append("group_name = %s")
        params.append(group_name)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            match_no,
            stage,
            group_name,
            date_et,
            time_et,
            home_team,
            away_team,
            venue,
            city
        FROM {qualified_name(schema, "world_cup_2026_known_fixtures")}
        {where_clause}
        ORDER BY match_no
        LIMIT %s
    """
    params.append(limit)
    return run_query(sql, tuple(params))


def query_head_to_head(team_a: str, team_b: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            match_date,
            home_team,
            away_team,
            home_score,
            away_score,
            tournament,
            neutral
        FROM {qualified_name(schema, "matches")}
        WHERE (home_team = %s AND away_team = %s)
           OR (home_team = %s AND away_team = %s)
        ORDER BY match_date DESC
    """
    return run_query(sql, (team_a, team_b, team_b, team_a))


def query_competition_summary(competition_type: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            competition_type,
            COUNT(*) AS matches,
            ROUND(AVG(home_score)::numeric, 3) AS avg_home_goals,
            ROUND(AVG(away_score)::numeric, 3) AS avg_away_goals,
            ROUND(
                AVG(CASE WHEN outcome = 'home_win' THEN 1.0 ELSE 0.0 END)::numeric,
                3
            ) AS home_win_rate,
            ROUND(AVG(CASE WHEN outcome = 'draw' THEN 1.0 ELSE 0.0 END)::numeric, 3) AS draw_rate
        FROM {qualified_name(schema, "matches")}
        WHERE competition_type = %s
        GROUP BY competition_type
    """
    return run_query(sql, (competition_type,))


def query_team_summary(team: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        WITH team_matches AS (
            SELECT
                CASE
                    WHEN home_team = %s AND outcome = 'home_win' THEN 'win'
                    WHEN away_team = %s AND outcome = 'away_win' THEN 'win'
                    WHEN outcome = 'draw' THEN 'draw'
                    ELSE 'loss'
                END AS team_result
            FROM {qualified_name(schema, "matches")}
            WHERE home_team = %s OR away_team = %s
        )
        SELECT
            s.team_name,
            s.latest_match_date,
            ROUND(s.latest_elo::numeric, 2) AS latest_elo,
            s.matches_played,
            COALESCE(SUM(CASE WHEN m.team_result = 'win' THEN 1 ELSE 0 END), 0) AS wins,
            COALESCE(SUM(CASE WHEN m.team_result = 'draw' THEN 1 ELSE 0 END), 0) AS draws,
            COALESCE(SUM(CASE WHEN m.team_result = 'loss' THEN 1 ELSE 0 END), 0) AS losses
        FROM {qualified_name(schema, "team_latest_snapshot")} AS s
        LEFT JOIN team_matches AS m
            ON s.team_name = %s
        WHERE s.team_name = %s
        GROUP BY s.team_name, s.latest_match_date, s.latest_elo, s.matches_played
    """
    return run_query(sql, (team, team, team, team, team, team))


def query_prediction_lookup(
    team: str | None,
    stage: str | None,
    group_name: str | None,
    limit: int,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    clauses: list[str] = []
    params: list[Any] = []

    if team:
        clauses.append("(home_team = %s OR away_team = %s)")
        params.extend([team, team])
    if stage:
        clauses.append("stage = %s")
        params.append(stage)
    if group_name:
        clauses.append("group_name = %s")
        params.append(group_name)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            match_no,
            stage,
            group_name,
            date_et,
            home_team,
            away_team,
            home_win_probability,
            draw_probability,
            away_win_probability,
            predicted_outcome
        FROM {qualified_name(schema, "baseline_prediction_summary")}
        {where_clause}
        ORDER BY match_no
        LIMIT %s
    """
    params.append(limit)
    return run_query(sql, tuple(params))


def query_group_overview(group_name: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            p.match_no,
            p.group_name,
            p.date_et,
            p.home_team,
            p.away_team,
            ROUND(hr.latest_elo::numeric, 2) AS home_team_elo,
            ROUND(ar.latest_elo::numeric, 2) AS away_team_elo,
            p.home_win_probability,
            p.draw_probability,
            p.away_win_probability,
            p.predicted_outcome
        FROM {qualified_name(schema, "baseline_prediction_summary")} AS p
        LEFT JOIN {qualified_name(schema, "ratings")} AS hr
            ON p.home_team = hr.team_name
        LEFT JOIN {qualified_name(schema, "ratings")} AS ar
            ON p.away_team = ar.team_name
        WHERE p.group_name = %s
        ORDER BY p.match_no
    """
    return run_query(sql, (group_name,))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run common Postgres research queries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    top_rated = subparsers.add_parser("top-rated", help="Show top-rated teams by latest Elo.")
    top_rated.add_argument("--limit", type=int, default=10)
    top_rated.add_argument("--output")

    team_history = subparsers.add_parser("team-history", help="Show recent matches for a team.")
    team_history.add_argument("--team", required=True)
    team_history.add_argument("--limit", type=int, default=10)
    team_history.add_argument("--output")

    fixtures = subparsers.add_parser("fixtures", help="Show known 2026 fixtures.")
    fixtures.add_argument("--stage")
    fixtures.add_argument("--group-name")
    fixtures.add_argument("--limit", type=int, default=20)
    fixtures.add_argument("--output")

    head_to_head = subparsers.add_parser(
        "head-to-head",
        help="Show historical head-to-head matches.",
    )
    head_to_head.add_argument("--team-a", required=True)
    head_to_head.add_argument("--team-b", required=True)
    head_to_head.add_argument("--output")

    competition = subparsers.add_parser(
        "competition-summary",
        help="Show aggregate metrics for a competition type.",
    )
    competition.add_argument("--competition-type", required=True)
    competition.add_argument("--output")

    team_summary = subparsers.add_parser("team-summary", help="Show aggregate summary for a team.")
    team_summary.add_argument("--team", required=True)
    team_summary.add_argument("--output")

    prediction_query = subparsers.add_parser(
        "prediction-query",
        help="Show baseline prediction rows filtered by team, stage, or group.",
    )
    prediction_query.add_argument("--team")
    prediction_query.add_argument("--stage")
    prediction_query.add_argument("--group-name")
    prediction_query.add_argument("--limit", type=int, default=20)
    prediction_query.add_argument("--output")

    group_overview = subparsers.add_parser(
        "group-overview",
        help="Show a World Cup group with Elo and baseline probabilities.",
    )
    group_overview.add_argument("--group-name", required=True)
    group_overview.add_argument("--output")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "top-rated":
        columns, rows = query_top_rated(args.limit)
    elif args.command == "team-history":
        columns, rows = query_team_history(args.team, args.limit)
    elif args.command == "fixtures":
        columns, rows = query_fixtures(args.stage, args.group_name, args.limit)
    elif args.command == "head-to-head":
        columns, rows = query_head_to_head(args.team_a, args.team_b)
    elif args.command == "competition-summary":
        columns, rows = query_competition_summary(args.competition_type)
    elif args.command == "team-summary":
        columns, rows = query_team_summary(args.team)
    elif args.command == "prediction-query":
        columns, rows = query_prediction_lookup(
            args.team,
            args.stage,
            args.group_name,
            args.limit,
        )
    elif args.command == "group-overview":
        columns, rows = query_group_overview(args.group_name)
    else:
        raise ValueError(f"Unknown command: {args.command}")

    output_path = getattr(args, "output", None)
    if output_path:
        write_output(output_path, columns, rows)
        print(f"wrote: {output_path}")
    else:
        print_table(columns, rows)


if __name__ == "__main__":
    main()
