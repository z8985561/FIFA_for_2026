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
    enhanced_predictions = qualified_table(schema, "enhanced_predictions")
    scoreline_analysis = qualified_table(schema, "scoreline_analysis")
    scoreline_value_bets = qualified_table(schema, "scoreline_value_bets")
    odds_raw_api_responses = qualified_table(schema, "odds_raw_api_responses")
    match_odds_features = qualified_table(schema, "match_odds_features")
    historical_match_odds_features = qualified_table(schema, "historical_match_odds_features")
    score_odds_collection_status = qualified_table(schema, "score_odds_collection_status")
    predicted_lineups = qualified_table(schema, "predicted_lineups")
    rankings = qualified_table(schema, "fifa_rankings_2026")
    squads = qualified_table(schema, "squads_2026")
    team_goal_form = qualified_table(schema, "team_goal_form_features")
    world_cup_teams = qualified_table(schema, "world_cup_teams_2026")
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
        "enhanced_prediction_summary": f"""
            CREATE OR REPLACE VIEW {qs}.enhanced_prediction_summary AS
            SELECT
                match_no,
                stage,
                group_name,
                date_et,
                home_team,
                away_team,
                home_confederation,
                away_confederation,
                same_confederation,
                confederation_pair,
                ROUND(home_latest_elo::numeric, 2) AS home_latest_elo,
                ROUND(away_latest_elo::numeric, 2) AS away_latest_elo,
                ROUND(elo_diff::numeric, 2) AS elo_diff,
                ROUND(expected_home_win::numeric, 4) AS expected_home_win,
                ROUND(home_rest_days::numeric, 2) AS home_rest_days,
                ROUND(away_rest_days::numeric, 2) AS away_rest_days,
                ROUND(rest_days_diff::numeric, 2) AS rest_days_diff,
                ROUND(points_per_match_diff_last_5::numeric, 4)
                    AS points_per_match_diff_last_5,
                ROUND(goal_diff_per_match_diff_last_5::numeric, 4)
                    AS goal_diff_per_match_diff_last_5,
                ROUND(win_rate_diff_last_10::numeric, 4) AS win_rate_diff_last_10,
                has_market_odds,
                ROUND(consensus_home_win_probability::numeric, 4)
                    AS consensus_home_win_probability,
                ROUND(consensus_draw_probability::numeric, 4)
                    AS consensus_draw_probability,
                ROUND(consensus_away_win_probability::numeric, 4)
                    AS consensus_away_win_probability,
                ROUND(avg_market_overround::numeric, 4) AS avg_market_overround,
                bookmaker_count,
                ROUND(market_entropy::numeric, 4) AS market_entropy,
                ROUND(favorite_probability::numeric, 4) AS favorite_probability,
                favorite_outcome,
                ROUND(home_win_probability::numeric, 4) AS home_win_probability,
                ROUND(draw_probability::numeric, 4) AS draw_probability,
                ROUND(away_win_probability::numeric, 4) AS away_win_probability,
                predicted_outcome,
                ROUND(blended_home_win_probability::numeric, 4)
                    AS blended_home_win_probability,
                ROUND(blended_draw_probability::numeric, 4)
                    AS blended_draw_probability,
                ROUND(blended_away_win_probability::numeric, 4)
                    AS blended_away_win_probability,
                blended_predicted_outcome,
                ROUND(model_market_home_gap::numeric, 4) AS model_market_home_gap,
                ROUND(model_market_draw_gap::numeric, 4) AS model_market_draw_gap,
                ROUND(model_market_away_gap::numeric, 4) AS model_market_away_gap
            FROM {enhanced_predictions}
        """,
        "scoreline_prediction_summary": f"""
            CREATE OR REPLACE VIEW {qs}.scoreline_prediction_summary AS
            SELECT
                match_no,
                stage,
                group_name,
                date_et,
                home_team,
                away_team,
                home_team_zh,
                away_team_zh,
                ROUND(raw_home_expected_goals::numeric, 3) AS raw_home_expected_goals,
                ROUND(raw_away_expected_goals::numeric, 3) AS raw_away_expected_goals,
                ROUND(home_expected_goals::numeric, 3) AS home_expected_goals,
                ROUND(away_expected_goals::numeric, 3) AS away_expected_goals,
                ROUND(home_lineup_goal_factor::numeric, 4) AS home_lineup_goal_factor,
                ROUND(away_lineup_goal_factor::numeric, 4) AS away_lineup_goal_factor,
                home_lineup_status,
                away_lineup_status,
                home_formation,
                away_formation,
                ROUND(dixon_coles_rho::numeric, 4) AS dixon_coles_rho,
                ROUND(score_home_win_probability::numeric, 4)
                    AS score_home_win_probability,
                ROUND(score_draw_probability::numeric, 4) AS score_draw_probability,
                ROUND(score_away_win_probability::numeric, 4)
                    AS score_away_win_probability,
                ROUND(over_2_5_probability::numeric, 4) AS over_2_5_probability,
                ROUND(under_2_5_probability::numeric, 4) AS under_2_5_probability,
                ROUND(both_teams_score_probability::numeric, 4)
                    AS both_teams_score_probability,
                ROUND(clean_sheet_home_probability::numeric, 4)
                    AS clean_sheet_home_probability,
                ROUND(clean_sheet_away_probability::numeric, 4)
                    AS clean_sheet_away_probability,
                scoreline_rank,
                scoreline,
                ROUND(scoreline_probability::numeric, 4) AS scoreline_probability
            FROM {scoreline_analysis}
        """,
        "score_odds_collection_status_summary": f"""
            CREATE OR REPLACE VIEW {qs}.score_odds_collection_status_summary AS
            SELECT
                match_no,
                date_et,
                home_team_zh || ' vs ' || away_team_zh AS matchup_zh,
                source_name,
                source_match_id,
                status,
                scoreline_count,
                source_url,
                attempted_urls,
                error_message,
                fetched_at
            FROM {score_odds_collection_status}
            ORDER BY match_no, source_name
        """,
        "scoreline_value_bet_summary": f"""
            CREATE OR REPLACE VIEW {qs}.scoreline_value_bet_summary AS
            SELECT
                match_no,
                stage,
                group_name,
                date_et,
                home_team_zh || ' vs ' || away_team_zh AS matchup_zh,
                scoreline_rank,
                scoreline,
                ROUND(model_probability::numeric, 4) AS model_probability,
                ROUND(model_fair_odds::numeric, 2) AS model_fair_odds,
                ROUND(best_decimal_odds::numeric, 2) AS best_decimal_odds,
                ROUND(market_edge::numeric, 4) AS market_edge,
                ROUND(kelly_fraction::numeric, 4) AS kelly_fraction,
                has_score_odds,
                value_signal,
                bookmaker_count,
                source_names,
                source_match_ids,
                source_urls,
                latest_fetched_at
            FROM {scoreline_value_bets}
            ORDER BY has_score_odds DESC, market_edge DESC NULLS LAST, model_probability DESC
        """,
        "odds_raw_api_response_inventory": f"""
            CREATE OR REPLACE VIEW {qs}.odds_raw_api_response_inventory AS
            SELECT
                source_file,
                payload_type,
                sport_key,
                fetched_at,
                file_size_bytes,
                jsonb_typeof(payload_json) AS payload_json_type,
                jsonb_typeof(metadata_json) AS metadata_json_type
            FROM {odds_raw_api_responses}
        """,
        "match_odds_feature_summary": f"""
            CREATE OR REPLACE VIEW {qs}.match_odds_feature_summary AS
            SELECT
                event_id,
                commence_time,
                home_team,
                away_team,
                ROUND(consensus_home_win_probability::numeric, 4)
                    AS consensus_home_win_probability,
                ROUND(consensus_draw_probability::numeric, 4)
                    AS consensus_draw_probability,
                ROUND(consensus_away_win_probability::numeric, 4)
                    AS consensus_away_win_probability,
                ROUND(avg_market_overround::numeric, 4) AS avg_market_overround,
                bookmaker_count,
                latest_fetched_at,
                ROUND(market_entropy::numeric, 4) AS market_entropy,
                ROUND(favorite_probability::numeric, 4) AS favorite_probability,
                favorite_outcome
            FROM {match_odds_features}
        """,
        "historical_match_odds_feature_summary": f"""
            CREATE OR REPLACE VIEW {qs}.historical_match_odds_feature_summary AS
            SELECT
                event_id,
                commence_time,
                home_team,
                away_team,
                ROUND(consensus_home_win_probability::numeric, 4)
                    AS consensus_home_win_probability,
                ROUND(consensus_draw_probability::numeric, 4)
                    AS consensus_draw_probability,
                ROUND(consensus_away_win_probability::numeric, 4)
                    AS consensus_away_win_probability,
                ROUND(avg_market_overround::numeric, 4) AS avg_market_overround,
                bookmaker_count,
                latest_fetched_at,
                ROUND(market_entropy::numeric, 4) AS market_entropy,
                ROUND(favorite_probability::numeric, 4) AS favorite_probability,
                favorite_outcome
            FROM {historical_match_odds_features}
        """,
        "predicted_lineup_summary": f"""
            CREATE OR REPLACE VIEW {qs}.predicted_lineup_summary AS
            SELECT
                match_no,
                match_date,
                group_name,
                home_team_zh || ' vs ' || away_team_zh AS matchup_zh,
                team_name_zh,
                lineup_status,
                formation,
                lineup_order,
                position_group,
                player_name,
                source_name,
                source_url
            FROM {predicted_lineups}
            ORDER BY match_no, team_name_zh, lineup_order
        """,
        "world_cup_team_profiles": f"""
            CREATE OR REPLACE VIEW {qs}.world_cup_team_profiles AS
            SELECT
                w.team_id,
                w.team_name,
                w.group_name,
                w.confederation,
                w.fifa_rank,
                w.ranking_source,
                w.ranking_date,
                w.latest_elo,
                w.latest_match_date,
                w.matches_played,
                w.first_match_date,
                w.last_match_date,
                w.total_matches,
                w.squad_size,
                w.squad_average_age,
                w.squad_total_caps
            FROM {world_cup_teams} AS w
        """,
        "squad_summary": f"""
            CREATE OR REPLACE VIEW {qs}.squad_summary AS
            SELECT
                s.team_name,
                s.group_name,
                COUNT(*) AS squad_size,
                ROUND(AVG(s.age)::numeric, 2) AS average_age,
                SUM(s.caps) AS total_caps,
                SUM(s.goals) AS total_goals,
                SUM(CASE WHEN s.captain THEN 1 ELSE 0 END) AS captains_listed
            FROM {squads} AS s
            GROUP BY s.team_name, s.group_name
        """,
        "rankings_snapshot": f"""
            CREATE OR REPLACE VIEW {qs}.rankings_snapshot AS
            SELECT
                r.fifa_rank,
                r.team_name,
                r.ranking_source,
                r.ranking_date,
                r.points
            FROM {rankings} AS r
            ORDER BY r.fifa_rank, r.team_name
        """,
        "team_goal_form_snapshot": f"""
            CREATE OR REPLACE VIEW {qs}.team_goal_form_snapshot AS
            SELECT
                team_name,
                as_of_date,
                matches_played,
                ROUND(goals_for_last_5::numeric, 3) AS goals_for_last_5,
                ROUND(goals_against_last_5::numeric, 3) AS goals_against_last_5,
                ROUND(goal_diff_last_5::numeric, 3) AS goal_diff_last_5,
                ROUND(clean_sheet_rate_last_5::numeric, 3) AS clean_sheet_rate_last_5,
                ROUND(btts_rate_last_5::numeric, 3) AS btts_rate_last_5,
                ROUND(avg_total_goals_last_5::numeric, 3) AS avg_total_goals_last_5,
                ROUND(goals_for_last_10::numeric, 3) AS goals_for_last_10,
                ROUND(goals_against_last_10::numeric, 3) AS goals_against_last_10,
                ROUND(goal_diff_last_10::numeric, 3) AS goal_diff_last_10,
                ROUND(clean_sheet_rate_last_10::numeric, 3) AS clean_sheet_rate_last_10,
                ROUND(btts_rate_last_10::numeric, 3) AS btts_rate_last_10,
                ROUND(avg_total_goals_last_10::numeric, 3) AS avg_total_goals_last_10,
                ROUND(goals_for_last_20::numeric, 3) AS goals_for_last_20,
                ROUND(goals_against_last_20::numeric, 3) AS goals_against_last_20,
                ROUND(goal_diff_last_20::numeric, 3) AS goal_diff_last_20,
                ROUND(clean_sheet_rate_last_20::numeric, 3) AS clean_sheet_rate_last_20,
                ROUND(btts_rate_last_20::numeric, 3) AS btts_rate_last_20,
                ROUND(avg_total_goals_last_20::numeric, 3) AS avg_total_goals_last_20
            FROM {team_goal_form}
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
