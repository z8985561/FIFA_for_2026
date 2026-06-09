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


def query_recent_form(team: str, limit: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        WITH recent_matches AS (
            SELECT
                match_date,
                home_team,
                away_team,
                home_score,
                away_score,
                tournament,
                CASE
                    WHEN home_team = %s AND outcome = 'home_win' THEN 'win'
                    WHEN away_team = %s AND outcome = 'away_win' THEN 'win'
                    WHEN outcome = 'draw' THEN 'draw'
                    ELSE 'loss'
                END AS result_for_team,
                CASE
                    WHEN home_team = %s THEN home_score
                    ELSE away_score
                END AS goals_for,
                CASE
                    WHEN home_team = %s THEN away_score
                    ELSE home_score
                END AS goals_against
            FROM {qualified_name(schema, "matches")}
            WHERE home_team = %s OR away_team = %s
            ORDER BY match_date DESC
            LIMIT %s
        )
        SELECT
            %s AS team_name,
            COUNT(*) AS matches_sampled,
            SUM(CASE WHEN result_for_team = 'win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result_for_team = 'draw' THEN 1 ELSE 0 END) AS draws,
            SUM(CASE WHEN result_for_team = 'loss' THEN 1 ELSE 0 END) AS losses,
            ROUND(AVG(goals_for)::numeric, 3) AS avg_goals_for,
            ROUND(AVG(goals_against)::numeric, 3) AS avg_goals_against
        FROM recent_matches
    """
    params = (team, team, team, team, team, team, limit, team)
    return run_query(sql, params)


def query_team_vs_field(team: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        WITH team_stats AS (
            SELECT
                s.team_name,
                s.latest_elo,
                s.matches_played,
                COALESCE(
                    SUM(
                        CASE
                            WHEN m.outcome = 'home_win' AND m.home_team = s.team_name THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )
                + COALESCE(
                    SUM(
                        CASE
                            WHEN m.outcome = 'away_win' AND m.away_team = s.team_name THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )
                AS wins,
                COALESCE(
                    SUM(
                        CASE
                            WHEN m.outcome = 'draw'
                            AND (
                                m.home_team = s.team_name
                                OR m.away_team = s.team_name
                            ) THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )
                AS draws,
                COALESCE(
                    SUM(
                        CASE
                            WHEN m.outcome = 'home_win' AND m.away_team = s.team_name THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )
                + COALESCE(
                    SUM(
                        CASE
                            WHEN m.outcome = 'away_win' AND m.home_team = s.team_name THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )
                AS losses
            FROM {qualified_name(schema, "team_latest_snapshot")} AS s
            LEFT JOIN {qualified_name(schema, "matches")} AS m
                ON s.team_name = m.home_team OR s.team_name = m.away_team
            WHERE s.team_name = %s
            GROUP BY s.team_name, s.latest_elo, s.matches_played
        ),
        field_stats AS (
            SELECT
                ROUND(AVG(latest_elo)::numeric, 2) AS avg_field_elo,
                ROUND(
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latest_elo)::numeric,
                    2
                ) AS median_field_elo,
                ROUND(MAX(latest_elo)::numeric, 2) AS max_field_elo
            FROM {qualified_name(schema, "team_latest_snapshot")}
        )
        SELECT
            t.team_name,
            ROUND(t.latest_elo::numeric, 2) AS latest_elo,
            t.matches_played,
            t.wins,
            t.draws,
            t.losses,
            f.avg_field_elo,
            f.median_field_elo,
            f.max_field_elo
        FROM team_stats AS t
        CROSS JOIN field_stats AS f
    """
    return run_query(sql, (team,))


def query_group_strength(group_name: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        WITH group_teams AS (
            SELECT home_team AS team_name
            FROM {qualified_name(schema, "fixtures_2026")}
            WHERE group_name = %s
            UNION
            SELECT away_team AS team_name
            FROM {qualified_name(schema, "fixtures_2026")}
            WHERE group_name = %s
        )
        SELECT
            %s AS group_name,
            gt.team_name,
            ROUND(r.latest_elo::numeric, 2) AS latest_elo,
            r.matches_played,
            ROUND(AVG(r.latest_elo) OVER ()::numeric, 2) AS group_avg_elo,
            ROUND((r.latest_elo - AVG(r.latest_elo) OVER ())::numeric, 2) AS elo_vs_group_avg
        FROM group_teams AS gt
        LEFT JOIN {qualified_name(schema, "ratings")} AS r
            ON gt.team_name = r.team_name
        ORDER BY latest_elo DESC NULLS LAST, gt.team_name
    """
    return run_query(sql, (group_name, group_name, group_name))


def query_prediction_extremes(
    mode: str,
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
    ordering = "ASC" if mode == "balanced" else "DESC"

    sql = f"""
        WITH prediction_scores AS (
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
                predicted_outcome,
                GREATEST(
                    home_win_probability,
                    draw_probability,
                    away_win_probability
                ) AS top_probability,
                (
                    home_win_probability
                    + draw_probability
                    + away_win_probability
                    - GREATEST(
                        home_win_probability,
                        draw_probability,
                        away_win_probability
                    )
                    - LEAST(
                        home_win_probability,
                        draw_probability,
                        away_win_probability
                    )
                ) AS middle_probability
            FROM {qualified_name(schema, "baseline_prediction_summary")}
            {where_clause}
        )
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
            predicted_outcome,
            ROUND(top_probability::numeric, 4) AS top_probability,
            ROUND(middle_probability::numeric, 4) AS middle_probability,
            ROUND((top_probability - middle_probability)::numeric, 4) AS confidence_gap
        FROM prediction_scores
        ORDER BY confidence_gap {ordering}, match_no
        LIMIT %s
    """
    params.append(limit)
    return run_query(sql, tuple(params))


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

    recent_form = subparsers.add_parser(
        "recent-form",
        help="Show recent form summary for a team.",
    )
    recent_form.add_argument("--team", required=True)
    recent_form.add_argument("--limit", type=int, default=10)
    recent_form.add_argument("--output")

    team_vs_field = subparsers.add_parser(
        "team-vs-field",
        help="Compare a team's profile against the full field.",
    )
    team_vs_field.add_argument("--team", required=True)
    team_vs_field.add_argument("--output")

    group_strength = subparsers.add_parser(
        "group-strength",
        help="Compare the teams inside one World Cup group.",
    )
    group_strength.add_argument("--group-name", required=True)
    group_strength.add_argument("--output")

    prediction_extremes = subparsers.add_parser(
        "prediction-extremes",
        help="Show the most balanced or most lopsided predicted matches.",
    )
    prediction_extremes.add_argument(
        "--mode",
        choices=["balanced", "lopsided"],
        default="balanced",
    )
    prediction_extremes.add_argument("--stage")
    prediction_extremes.add_argument("--group-name")
    prediction_extremes.add_argument("--limit", type=int, default=10)
    prediction_extremes.add_argument("--output")

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
    elif args.command == "recent-form":
        columns, rows = query_recent_form(args.team, args.limit)
    elif args.command == "team-vs-field":
        columns, rows = query_team_vs_field(args.team)
    elif args.command == "group-strength":
        columns, rows = query_group_strength(args.group_name)
    elif args.command == "prediction-extremes":
        columns, rows = query_prediction_extremes(
            args.mode,
            args.stage,
            args.group_name,
            args.limit,
        )
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
