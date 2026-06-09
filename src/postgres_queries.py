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


def query_enhanced_prediction_lookup(
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
            elo_diff,
            expected_home_win,
            home_rest_days,
            away_rest_days,
            points_per_match_diff_last_5,
            goal_diff_per_match_diff_last_5,
            win_rate_diff_last_10,
            home_win_probability,
            draw_probability,
            away_win_probability,
            predicted_outcome
        FROM {qualified_name(schema, "enhanced_prediction_summary")}
        {where_clause}
        ORDER BY match_no
        LIMIT %s
    """
    params.append(limit)
    return run_query(sql, tuple(params))


def query_scoreline_lookup(
    team: str | None,
    group_name: str | None,
    match_no: int | None,
    limit: int,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    clauses: list[str] = []
    params: list[Any] = []

    if team:
        clauses.append("(home_team = %s OR away_team = %s)")
        params.extend([team, team])
    if group_name:
        clauses.append("group_name = %s")
        params.append(group_name)
    if match_no:
        clauses.append("match_no = %s")
        params.append(match_no)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            match_no,
            group_name,
            date_et,
            home_team,
            away_team,
            home_expected_goals,
            away_expected_goals,
            score_home_win_probability,
            score_draw_probability,
            score_away_win_probability,
            over_2_5_probability,
            both_teams_score_probability,
            scoreline_rank,
            scoreline,
            scoreline_probability
        FROM {qualified_name(schema, "scoreline_prediction_summary")}
        {where_clause}
        ORDER BY match_no, scoreline_rank
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


def query_world_cup_teams(
    group_name: str | None,
    confederation: str | None,
    limit: int,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    clauses: list[str] = []
    params: list[Any] = []

    if group_name:
        clauses.append("group_name = %s")
        params.append(group_name)
    if confederation:
        clauses.append("confederation = %s")
        params.append(confederation)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            team_name,
            group_name,
            confederation,
            fifa_rank,
            ROUND(latest_elo::numeric, 2) AS latest_elo,
            squad_size,
            ROUND(squad_average_age::numeric, 2) AS squad_average_age,
            squad_total_caps
        FROM {qualified_name(schema, "world_cup_team_profiles")}
        {where_clause}
        ORDER BY fifa_rank NULLS LAST, latest_elo DESC NULLS LAST, team_name
        LIMIT %s
    """
    params.append(limit)
    return run_query(sql, tuple(params))


def query_squad(team: str, position: str | None) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    clauses = ["team_name = %s"]
    params: list[Any] = [team]

    if position:
        clauses.append("position = %s")
        params.append(position)

    sql = f"""
        SELECT
            team_name,
            group_name,
            shirt_number,
            position,
            player_name,
            captain,
            age,
            caps,
            goals,
            club
        FROM {qualified_name(schema, "squads_2026")}
        WHERE {' AND '.join(clauses)}
        ORDER BY shirt_number
    """
    return run_query(sql, tuple(params))


def query_squad_summary(team: str | None) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    where_clause = "WHERE team_name = %s" if team else ""
    params: tuple[Any, ...] = (team,) if team else ()
    sql = f"""
        SELECT
            team_name,
            group_name,
            squad_size,
            average_age,
            total_caps,
            total_goals,
            captains_listed
        FROM {qualified_name(schema, "squad_summary")}
        {where_clause}
        ORDER BY average_age, team_name
    """
    return run_query(sql, params)


def query_group_profiles(group_name: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            team_name,
            confederation,
            fifa_rank,
            ROUND(latest_elo::numeric, 2) AS latest_elo,
            squad_size,
            ROUND(squad_average_age::numeric, 2) AS squad_average_age,
            squad_total_caps
        FROM {qualified_name(schema, "world_cup_team_profiles")}
        WHERE group_name = %s
        ORDER BY fifa_rank NULLS LAST, latest_elo DESC NULLS LAST, team_name
    """
    return run_query(sql, (group_name,))


def query_squad_composition(team: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        SELECT
            team_name,
            group_name,
            COUNT(*) AS squad_size,
            ROUND(AVG(age)::numeric, 2) AS average_age,
            ROUND(AVG(caps)::numeric, 2) AS average_caps,
            SUM(caps) AS total_caps,
            SUM(goals) AS total_goals,
            SUM(CASE WHEN position = 'GK' THEN 1 ELSE 0 END) AS goalkeepers,
            SUM(CASE WHEN position = 'DF' THEN 1 ELSE 0 END) AS defenders,
            SUM(CASE WHEN position = 'MF' THEN 1 ELSE 0 END) AS midfielders,
            SUM(CASE WHEN position = 'FW' THEN 1 ELSE 0 END) AS forwards,
            MIN(age) AS youngest_age,
            MAX(age) AS oldest_age
        FROM {qualified_name(schema, "squads_2026")}
        WHERE team_name = %s
        GROUP BY team_name, group_name
    """
    return run_query(sql, (team,))


def query_team_schedule_difficulty(team: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    sql = f"""
        WITH team_schedule AS (
            SELECT
                f.match_no,
                f.stage,
                f.group_name,
                f.date_et,
                CASE
                    WHEN f.home_team = %s THEN f.away_team
                    ELSE f.home_team
                END AS opponent_team,
                CASE
                    WHEN f.home_team = %s THEN 'home'
                    ELSE 'away'
                END AS team_side
            FROM {qualified_name(schema, "fixtures_2026")} AS f
            WHERE f.home_team = %s OR f.away_team = %s
        )
        SELECT
            %s AS team_name,
            s.match_no,
            s.stage,
            s.group_name,
            s.date_et,
            s.team_side,
            s.opponent_team,
            p.fifa_rank AS opponent_fifa_rank,
            ROUND(p.latest_elo::numeric, 2) AS opponent_latest_elo,
            p.squad_total_caps AS opponent_squad_total_caps,
            ROUND(AVG(p.latest_elo) OVER ()::numeric, 2) AS avg_opponent_elo,
            ROUND(AVG(p.fifa_rank) OVER ()::numeric, 2) AS avg_opponent_fifa_rank
        FROM team_schedule AS s
        LEFT JOIN {qualified_name(schema, "world_cup_team_profiles")} AS p
            ON s.opponent_team = p.team_name
        ORDER BY s.match_no
    """
    return run_query(sql, (team, team, team, team, team))


def query_group_difficulty(
    limit: int,
    group_name: str | None = None,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    where_clause = "WHERE group_name = %s" if group_name else ""
    params: tuple[Any, ...] = (group_name, limit) if group_name else (limit,)
    sql = f"""
        WITH grouped AS (
            SELECT
                group_name,
                ROUND(AVG(latest_elo)::numeric, 2) AS avg_group_elo,
                ROUND(AVG(fifa_rank)::numeric, 2) AS avg_group_fifa_rank,
                ROUND(AVG(squad_average_age)::numeric, 2) AS avg_squad_age,
                ROUND(AVG(squad_total_caps)::numeric, 2) AS avg_squad_caps,
                ROUND((MAX(latest_elo) - MIN(latest_elo))::numeric, 2) AS elo_spread
            FROM {qualified_name(schema, "world_cup_team_profiles")}
            GROUP BY group_name
        ),
        ranked AS (
            SELECT
                DENSE_RANK() OVER (
                    ORDER BY avg_group_elo DESC NULLS LAST, avg_group_fifa_rank ASC NULLS LAST
                ) AS difficulty_rank,
                group_name,
                avg_group_elo,
                avg_group_fifa_rank,
                avg_squad_age,
                avg_squad_caps,
                elo_spread
            FROM grouped
        )
        SELECT
            difficulty_rank,
            group_name,
            avg_group_elo,
            avg_group_fifa_rank,
            avg_squad_age,
            avg_squad_caps,
            elo_spread
        FROM ranked
        {where_clause}
        ORDER BY difficulty_rank, group_name
        LIMIT %s
    """
    return run_query(sql, params)


def query_match_features(
    team: str | None,
    group_name: str | None,
    limit: int,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = load_postgres_view_config().schema
    clauses: list[str] = []
    params: list[Any] = []

    if team:
        clauses.append("(home_team = %s OR away_team = %s)")
        params.extend([team, team])
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
            home_fifa_rank,
            away_fifa_rank,
            home_rank_advantage,
            ROUND(home_latest_elo::numeric, 2) AS home_latest_elo,
            ROUND(away_latest_elo::numeric, 2) AS away_latest_elo,
            ROUND(elo_diff::numeric, 2) AS elo_diff,
            ROUND(expected_home_win::numeric, 4) AS expected_home_win,
            squad_total_caps_diff,
            ROUND(squad_average_age_diff::numeric, 2) AS squad_average_age_diff,
            group_difficulty_rank,
            ROUND(group_avg_elo::numeric, 2) AS group_avg_elo,
            ROUND(group_elo_spread::numeric, 2) AS group_elo_spread
        FROM {qualified_name(schema, "match_feature_store_2026")}
        {where_clause}
        ORDER BY match_no
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

    enhanced_prediction_query = subparsers.add_parser(
        "enhanced-prediction-query",
        help="Show enhanced prediction rows with recent-form context.",
    )
    enhanced_prediction_query.add_argument("--team")
    enhanced_prediction_query.add_argument("--stage")
    enhanced_prediction_query.add_argument("--group-name")
    enhanced_prediction_query.add_argument("--limit", type=int, default=20)
    enhanced_prediction_query.add_argument("--output")

    scoreline_query = subparsers.add_parser(
        "scoreline-query",
        help="Show exact-score probabilities from the scoreline model.",
    )
    scoreline_query.add_argument("--team")
    scoreline_query.add_argument("--group-name")
    scoreline_query.add_argument("--match-no", type=int)
    scoreline_query.add_argument("--limit", type=int, default=40)
    scoreline_query.add_argument("--output")

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

    world_cup_teams = subparsers.add_parser(
        "world-cup-teams",
        help="Show qualified World Cup teams with ranking and squad profile fields.",
    )
    world_cup_teams.add_argument("--group-name")
    world_cup_teams.add_argument("--confederation")
    world_cup_teams.add_argument("--limit", type=int, default=60)
    world_cup_teams.add_argument("--output")

    squad = subparsers.add_parser(
        "squad",
        help="Show the full final squad for a team.",
    )
    squad.add_argument("--team", required=True)
    squad.add_argument("--position")
    squad.add_argument("--output")

    squad_summary = subparsers.add_parser(
        "squad-summary",
        help="Show squad summary metrics for one team or all teams.",
    )
    squad_summary.add_argument("--team")
    squad_summary.add_argument("--output")

    group_profiles = subparsers.add_parser(
        "group-profiles",
        help="Show World Cup team profile fields for one group.",
    )
    group_profiles.add_argument("--group-name", required=True)
    group_profiles.add_argument("--output")

    squad_composition = subparsers.add_parser(
        "squad-composition",
        help="Show squad age, caps, and position structure for one team.",
    )
    squad_composition.add_argument("--team", required=True)
    squad_composition.add_argument("--output")

    team_schedule_difficulty = subparsers.add_parser(
        "team-schedule-difficulty",
        help="Show a team's 2026 opponent strength profile.",
    )
    team_schedule_difficulty.add_argument("--team", required=True)
    team_schedule_difficulty.add_argument("--output")

    group_difficulty = subparsers.add_parser(
        "group-difficulty",
        help="Compare World Cup group difficulty using rank and Elo context.",
    )
    group_difficulty.add_argument("--limit", type=int, default=12)
    group_difficulty.add_argument("--output")

    match_features = subparsers.add_parser(
        "match-features",
        help="Show model-ready features for known 2026 fixtures.",
    )
    match_features.add_argument("--team")
    match_features.add_argument("--group-name")
    match_features.add_argument("--limit", type=int, default=20)
    match_features.add_argument("--output")

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
    elif args.command == "enhanced-prediction-query":
        columns, rows = query_enhanced_prediction_lookup(
            args.team,
            args.stage,
            args.group_name,
            args.limit,
        )
    elif args.command == "scoreline-query":
        columns, rows = query_scoreline_lookup(
            args.team,
            args.group_name,
            args.match_no,
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
    elif args.command == "world-cup-teams":
        columns, rows = query_world_cup_teams(
            args.group_name,
            args.confederation,
            args.limit,
        )
    elif args.command == "squad":
        columns, rows = query_squad(args.team, args.position)
    elif args.command == "squad-summary":
        columns, rows = query_squad_summary(args.team)
    elif args.command == "group-profiles":
        columns, rows = query_group_profiles(args.group_name)
    elif args.command == "squad-composition":
        columns, rows = query_squad_composition(args.team)
    elif args.command == "team-schedule-difficulty":
        columns, rows = query_team_schedule_difficulty(args.team)
    elif args.command == "group-difficulty":
        columns, rows = query_group_difficulty(args.limit)
    elif args.command == "match-features":
        columns, rows = query_match_features(args.team, args.group_name, args.limit)
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
