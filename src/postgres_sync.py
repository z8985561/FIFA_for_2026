from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg

from .data_pipeline import prepare_research_data
from .enhanced_features import enhanced_feature_columns
from .enhanced_model import prepare_enhanced_outputs
from .feature_store import prepare_match_feature_store
from .goal_form_features import prepare_goal_form_features
from .lineups_pipeline import prepare_predicted_lineups
from .project_paths import (
    BASELINE_PREDICTIONS_PATH,
    DATABASE_PATH,
    ENHANCED_PREDICTIONS_PATH,
    FIFA_RANKINGS_PATH,
    FIXTURES_PATH,
    HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH,
    HISTORICAL_MATCH_FEATURE_STORE_PATH,
    HISTORICAL_MATCH_ODDS_FEATURES_PATH,
    MARKET_ODDS_SNAPSHOTS_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    MATCH_ODDS_FEATURES_PATH,
    MATCHES_PATH,
    PREDICTED_LINEUPS_PATH,
    RATINGS_PATH,
    RAW_ODDS_DIR,
    SCORE_ODDS_COLLECTION_STATUS_PATH,
    SCORE_ODDS_FEATURES_PATH,
    SCORE_ODDS_HISTORY_PATH,
    SCORE_ODDS_SNAPSHOTS_PATH,
    SCORELINE_ANALYSIS_PATH,
    SCORELINE_VALUE_BETS_PATH,
    SQUADS_2026_PATH,
    TEAM_GOAL_FORM_FEATURES_PATH,
    TEAMS_PATH,
    WORLD_CUP_TEAMS_2026_PATH,
)
from .score_odds_pipeline import prepare_score_odds_features
from .scoreline_model import prepare_scoreline_analysis
from .value_bets_report import prepare_value_bets_report
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
    "home_confederation",
    "away_confederation",
    "same_confederation",
    "confederation_pair",
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
    "has_market_odds",
    "consensus_home_win_probability",
    "consensus_draw_probability",
    "consensus_away_win_probability",
    "avg_market_overround",
    "min_market_overround",
    "max_market_overround",
    "bookmaker_count",
    "latest_bookmaker_update",
    "latest_market_update",
    "latest_fetched_at",
    "market_entropy",
    "favorite_probability",
    "favorite_outcome",
    "away_win_probability",
    "draw_probability",
    "home_win_probability",
    "predicted_outcome",
    "blended_away_win_probability",
    "blended_draw_probability",
    "blended_home_win_probability",
    "blended_predicted_outcome",
    "model_market_home_gap",
    "model_market_draw_gap",
    "model_market_away_gap",
]

SCORELINE_ANALYSIS_COLUMNS = [
    "match_no",
    "stage",
    "group_name",
    "date_et",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "raw_home_expected_goals",
    "raw_away_expected_goals",
    "home_expected_goals",
    "away_expected_goals",
    "home_lineup_goal_factor",
    "away_lineup_goal_factor",
    "home_lineup_log_adjustment",
    "away_lineup_log_adjustment",
    "home_lineup_status",
    "away_lineup_status",
    "home_formation",
    "away_formation",
    "dixon_coles_rho",
    "score_home_win_probability",
    "score_draw_probability",
    "score_away_win_probability",
    "over_2_5_probability",
    "under_2_5_probability",
    "both_teams_score_probability",
    "clean_sheet_home_probability",
    "clean_sheet_away_probability",
    "scoreline_rank",
    "scoreline",
    "scoreline_probability",
]

TEAM_GOAL_FORM_COLUMNS = [
    "team_name",
    "as_of_date",
    "matches_played",
    "goals_for_last_5",
    "goals_against_last_5",
    "goal_diff_last_5",
    "clean_sheet_rate_last_5",
    "btts_rate_last_5",
    "avg_total_goals_last_5",
    "goals_for_last_10",
    "goals_against_last_10",
    "goal_diff_last_10",
    "clean_sheet_rate_last_10",
    "btts_rate_last_10",
    "avg_total_goals_last_10",
    "goals_for_last_20",
    "goals_against_last_20",
    "goal_diff_last_20",
    "clean_sheet_rate_last_20",
    "btts_rate_last_20",
    "avg_total_goals_last_20",
]

ODDS_RAW_API_RESPONSE_COLUMNS = [
    "source_file",
    "source_path",
    "payload_type",
    "sport_key",
    "fetched_at",
    "file_size_bytes",
    "payload_json",
    "metadata_json",
]

MARKET_ODDS_SNAPSHOT_COLUMNS = [
    "source_file",
    "request_label",
    "request_markets",
    "request_regions",
    "fetched_at",
    "event_id",
    "sport_key",
    "sport_title",
    "commence_time",
    "home_team",
    "away_team",
    "bookmaker_key",
    "bookmaker_title",
    "bookmaker_last_update",
    "market_key",
    "market_last_update",
    "outcome_name",
    "price",
    "point",
]

MATCH_ODDS_FEATURE_COLUMNS = [
    "event_id",
    "commence_time",
    "home_team",
    "away_team",
    "consensus_home_win_probability",
    "consensus_draw_probability",
    "consensus_away_win_probability",
    "avg_market_overround",
    "min_market_overround",
    "max_market_overround",
    "bookmaker_count",
    "latest_bookmaker_update",
    "latest_market_update",
    "latest_fetched_at",
    "consensus_fair_probability_sum",
    "market_entropy",
    "favorite_probability",
    "favorite_outcome",
]

PREDICTED_LINEUP_COLUMNS = [
    "match_no",
    "match_date",
    "group_name",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "team_name",
    "team_name_zh",
    "lineup_status",
    "formation",
    "lineup_order",
    "position_group",
    "player_name",
    "source_name",
    "source_url",
]

SCORE_ODDS_SNAPSHOT_COLUMNS = [
    "match_no",
    "stage",
    "group_name",
    "date_et",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "scoreline",
    "bookmaker_key",
    "bookmaker_title",
    "american_odds",
    "decimal_odds",
    "raw_implied_probability",
    "source_name",
    "source_url",
    "source_match_id",
    "fetched_at",
]

SCORE_ODDS_FEATURE_COLUMNS = [
    "match_no",
    "stage",
    "group_name",
    "date_et",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "scoreline",
    "best_decimal_odds",
    "average_decimal_odds",
    "raw_market_implied_probability",
    "bookmaker_count",
    "latest_fetched_at",
    "source_names",
    "source_urls",
    "source_match_ids",
    "listed_score_market_overround_proxy",
    "listed_score_fair_probability",
]

SCORE_ODDS_COLLECTION_STATUS_COLUMNS = [
    "match_no",
    "date_et",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "source_name",
    "source_url",
    "source_match_id",
    "attempted_urls",
    "status",
    "scoreline_count",
    "error_message",
    "fetched_at",
]

SCORELINE_VALUE_BET_COLUMNS = [
    "match_no",
    "stage",
    "group_name",
    "date_et",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "scoreline_rank",
    "scoreline",
    "model_probability",
    "model_fair_odds",
    "best_decimal_odds",
    "average_decimal_odds",
    "raw_market_implied_probability",
    "listed_score_fair_probability",
    "listed_score_market_overround_proxy",
    "market_edge",
    "kelly_fraction",
    "has_score_odds",
    "value_signal",
    "bookmaker_count",
    "source_names",
    "source_urls",
    "source_match_ids",
    "latest_fetched_at",
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
    "team_goal_form_features": TEAM_GOAL_FORM_COLUMNS,
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
    "odds_raw_api_responses": ODDS_RAW_API_RESPONSE_COLUMNS,
    "market_odds_snapshots": MARKET_ODDS_SNAPSHOT_COLUMNS,
    "match_odds_features": MATCH_ODDS_FEATURE_COLUMNS,
    "historical_market_odds_snapshots": MARKET_ODDS_SNAPSHOT_COLUMNS,
    "historical_match_odds_features": MATCH_ODDS_FEATURE_COLUMNS,
    "predicted_lineups": PREDICTED_LINEUP_COLUMNS,
    "score_odds_snapshots": SCORE_ODDS_SNAPSHOT_COLUMNS,
    "score_odds_history": SCORE_ODDS_SNAPSHOT_COLUMNS,
    "score_odds_features": SCORE_ODDS_FEATURE_COLUMNS,
    "score_odds_collection_status": SCORE_ODDS_COLLECTION_STATUS_COLUMNS,
    "enhanced_predictions": ENHANCED_PREDICTION_COLUMNS,
    "scoreline_analysis": SCORELINE_ANALYSIS_COLUMNS,
    "scoreline_value_bets": SCORELINE_VALUE_BET_COLUMNS,
}

MANAGED_POSTGRES_TABLES = tuple(POSTGRES_TABLE_COLUMNS)


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
        TEAM_GOAL_FORM_FEATURES_PATH,
        MATCH_FEATURE_STORE_2026_PATH,
        HISTORICAL_MATCH_FEATURE_STORE_PATH,
        ENHANCED_PREDICTIONS_PATH,
        SCORELINE_ANALYSIS_PATH,
        MARKET_ODDS_SNAPSHOTS_PATH,
        MATCH_ODDS_FEATURES_PATH,
        HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH,
        HISTORICAL_MATCH_ODDS_FEATURES_PATH,
        PREDICTED_LINEUPS_PATH,
        SCORE_ODDS_SNAPSHOTS_PATH,
        SCORE_ODDS_FEATURES_PATH,
        SCORE_ODDS_COLLECTION_STATUS_PATH,
        SCORELINE_VALUE_BETS_PATH,
    ]
    if any(not path.exists() for path in required_paths):
        prepare_research_data()
        prepare_world_cup_identity_data()
        prepare_goal_form_features()
        prepare_match_feature_store()
        prepare_enhanced_outputs()
        prepare_scoreline_analysis()
        prepare_predicted_lineups()
        prepare_score_odds_features()
        prepare_value_bets_report()


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
    team_goal_form_table = qualified_table(schema, "team_goal_form_features")
    match_feature_store_table = qualified_table(schema, "match_feature_store_2026")
    historical_feature_store_table = qualified_table(schema, "historical_match_feature_store")
    odds_raw_api_responses_table = qualified_table(schema, "odds_raw_api_responses")
    market_odds_snapshots_table = qualified_table(schema, "market_odds_snapshots")
    match_odds_features_table = qualified_table(schema, "match_odds_features")
    historical_market_odds_snapshots_table = qualified_table(
        schema,
        "historical_market_odds_snapshots",
    )
    historical_match_odds_features_table = qualified_table(
        schema,
        "historical_match_odds_features",
    )
    predicted_lineups_table = qualified_table(schema, "predicted_lineups")
    score_odds_snapshots_table = qualified_table(schema, "score_odds_snapshots")
    score_odds_history_table = qualified_table(schema, "score_odds_history")
    score_odds_features_table = qualified_table(schema, "score_odds_features")
    score_odds_collection_status_table = qualified_table(
        schema,
        "score_odds_collection_status",
    )
    enhanced_predictions_table = qualified_table(schema, "enhanced_predictions")
    scoreline_analysis_table = qualified_table(schema, "scoreline_analysis")
    scoreline_value_bets_table = qualified_table(schema, "scoreline_value_bets")
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
        CREATE TABLE IF NOT EXISTS {team_goal_form_table} (
            team_name TEXT PRIMARY KEY,
            as_of_date DATE NOT NULL,
            matches_played BIGINT NOT NULL,
            goals_for_last_5 DOUBLE PRECISION NOT NULL,
            goals_against_last_5 DOUBLE PRECISION NOT NULL,
            goal_diff_last_5 DOUBLE PRECISION NOT NULL,
            clean_sheet_rate_last_5 DOUBLE PRECISION NOT NULL,
            btts_rate_last_5 DOUBLE PRECISION NOT NULL,
            avg_total_goals_last_5 DOUBLE PRECISION NOT NULL,
            goals_for_last_10 DOUBLE PRECISION NOT NULL,
            goals_against_last_10 DOUBLE PRECISION NOT NULL,
            goal_diff_last_10 DOUBLE PRECISION NOT NULL,
            clean_sheet_rate_last_10 DOUBLE PRECISION NOT NULL,
            btts_rate_last_10 DOUBLE PRECISION NOT NULL,
            avg_total_goals_last_10 DOUBLE PRECISION NOT NULL,
            goals_for_last_20 DOUBLE PRECISION NOT NULL,
            goals_against_last_20 DOUBLE PRECISION NOT NULL,
            goal_diff_last_20 DOUBLE PRECISION NOT NULL,
            clean_sheet_rate_last_20 DOUBLE PRECISION NOT NULL,
            btts_rate_last_20 DOUBLE PRECISION NOT NULL,
            avg_total_goals_last_20 DOUBLE PRECISION NOT NULL
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
        CREATE TABLE IF NOT EXISTS {odds_raw_api_responses_table} (
            source_file TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            payload_type TEXT NOT NULL,
            sport_key TEXT,
            fetched_at TIMESTAMPTZ,
            file_size_bytes BIGINT NOT NULL,
            payload_json JSONB NOT NULL,
            metadata_json JSONB NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {market_odds_snapshots_table} (
            source_file TEXT NOT NULL,
            request_label TEXT,
            request_markets TEXT,
            request_regions TEXT,
            fetched_at TIMESTAMPTZ,
            event_id TEXT NOT NULL,
            sport_key TEXT,
            sport_title TEXT,
            commence_time TIMESTAMPTZ,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            bookmaker_key TEXT NOT NULL,
            bookmaker_title TEXT,
            bookmaker_last_update TIMESTAMPTZ,
            market_key TEXT NOT NULL,
            market_last_update TIMESTAMPTZ,
            outcome_name TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            point DOUBLE PRECISION
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {match_odds_features_table} (
            event_id TEXT PRIMARY KEY,
            commence_time TIMESTAMPTZ,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            consensus_home_win_probability DOUBLE PRECISION NOT NULL,
            consensus_draw_probability DOUBLE PRECISION NOT NULL,
            consensus_away_win_probability DOUBLE PRECISION NOT NULL,
            avg_market_overround DOUBLE PRECISION,
            min_market_overround DOUBLE PRECISION,
            max_market_overround DOUBLE PRECISION,
            bookmaker_count BIGINT,
            latest_bookmaker_update TIMESTAMPTZ,
            latest_market_update TIMESTAMPTZ,
            latest_fetched_at TIMESTAMPTZ,
            consensus_fair_probability_sum DOUBLE PRECISION,
            market_entropy DOUBLE PRECISION,
            favorite_probability DOUBLE PRECISION,
            favorite_outcome TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {historical_market_odds_snapshots_table} (
            source_file TEXT NOT NULL,
            request_label TEXT,
            request_markets TEXT,
            request_regions TEXT,
            fetched_at TIMESTAMPTZ,
            event_id TEXT NOT NULL,
            sport_key TEXT,
            sport_title TEXT,
            commence_time TIMESTAMPTZ,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            bookmaker_key TEXT NOT NULL,
            bookmaker_title TEXT,
            bookmaker_last_update TIMESTAMPTZ,
            market_key TEXT NOT NULL,
            market_last_update TIMESTAMPTZ,
            outcome_name TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            point DOUBLE PRECISION
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {historical_match_odds_features_table} (
            event_id TEXT PRIMARY KEY,
            commence_time TIMESTAMPTZ,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            consensus_home_win_probability DOUBLE PRECISION NOT NULL,
            consensus_draw_probability DOUBLE PRECISION NOT NULL,
            consensus_away_win_probability DOUBLE PRECISION NOT NULL,
            avg_market_overround DOUBLE PRECISION,
            min_market_overround DOUBLE PRECISION,
            max_market_overround DOUBLE PRECISION,
            bookmaker_count BIGINT,
            latest_bookmaker_update TIMESTAMPTZ,
            latest_market_update TIMESTAMPTZ,
            latest_fetched_at TIMESTAMPTZ,
            consensus_fair_probability_sum DOUBLE PRECISION,
            market_entropy DOUBLE PRECISION,
            favorite_probability DOUBLE PRECISION,
            favorite_outcome TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {predicted_lineups_table} (
            match_no BIGINT NOT NULL,
            match_date DATE NOT NULL,
            group_name TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT NOT NULL,
            away_team_zh TEXT NOT NULL,
            team_name TEXT NOT NULL,
            team_name_zh TEXT NOT NULL,
            lineup_status TEXT NOT NULL,
            formation TEXT NOT NULL,
            lineup_order INTEGER NOT NULL,
            position_group TEXT NOT NULL,
            player_name TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            PRIMARY KEY (match_no, team_name, lineup_status, lineup_order)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {score_odds_snapshots_table} (
            match_no BIGINT NOT NULL,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT,
            away_team_zh TEXT,
            scoreline TEXT NOT NULL,
            bookmaker_key TEXT NOT NULL,
            bookmaker_title TEXT NOT NULL,
            american_odds TEXT NOT NULL,
            decimal_odds DOUBLE PRECISION NOT NULL,
            raw_implied_probability DOUBLE PRECISION NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            source_match_id TEXT,
            fetched_at TIMESTAMPTZ NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {score_odds_history_table} (
            match_no BIGINT NOT NULL,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT,
            away_team_zh TEXT,
            scoreline TEXT NOT NULL,
            bookmaker_key TEXT NOT NULL,
            bookmaker_title TEXT NOT NULL,
            american_odds TEXT NOT NULL,
            decimal_odds DOUBLE PRECISION NOT NULL,
            raw_implied_probability DOUBLE PRECISION NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            source_match_id TEXT,
            fetched_at TIMESTAMPTZ NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {score_odds_features_table} (
            match_no BIGINT NOT NULL,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT,
            away_team_zh TEXT,
            scoreline TEXT NOT NULL,
            best_decimal_odds DOUBLE PRECISION NOT NULL,
            average_decimal_odds DOUBLE PRECISION NOT NULL,
            raw_market_implied_probability DOUBLE PRECISION NOT NULL,
            bookmaker_count BIGINT NOT NULL,
            latest_fetched_at TIMESTAMPTZ NOT NULL,
            source_names TEXT,
            source_urls TEXT,
            source_match_ids TEXT,
            listed_score_market_overround_proxy DOUBLE PRECISION NOT NULL,
            listed_score_fair_probability DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (match_no, scoreline)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {score_odds_collection_status_table} (
            match_no BIGINT NOT NULL,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT,
            away_team_zh TEXT,
            source_name TEXT NOT NULL,
            source_url TEXT,
            source_match_id TEXT,
            attempted_urls TEXT,
            status TEXT NOT NULL,
            scoreline_count BIGINT NOT NULL,
            error_message TEXT,
            fetched_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (match_no, source_name)
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
            home_confederation TEXT NOT NULL,
            away_confederation TEXT NOT NULL,
            same_confederation BOOLEAN NOT NULL,
            confederation_pair TEXT NOT NULL,
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
            has_market_odds BOOLEAN NOT NULL,
            consensus_home_win_probability DOUBLE PRECISION,
            consensus_draw_probability DOUBLE PRECISION,
            consensus_away_win_probability DOUBLE PRECISION,
            avg_market_overround DOUBLE PRECISION,
            min_market_overround DOUBLE PRECISION,
            max_market_overround DOUBLE PRECISION,
            bookmaker_count BIGINT,
            latest_bookmaker_update TIMESTAMPTZ,
            latest_market_update TIMESTAMPTZ,
            latest_fetched_at TIMESTAMPTZ,
            market_entropy DOUBLE PRECISION,
            favorite_probability DOUBLE PRECISION,
            favorite_outcome TEXT,
            away_win_probability DOUBLE PRECISION NOT NULL,
            draw_probability DOUBLE PRECISION NOT NULL,
            home_win_probability DOUBLE PRECISION NOT NULL,
            predicted_outcome TEXT NOT NULL,
            blended_away_win_probability DOUBLE PRECISION NOT NULL,
            blended_draw_probability DOUBLE PRECISION NOT NULL,
            blended_home_win_probability DOUBLE PRECISION NOT NULL,
            blended_predicted_outcome TEXT NOT NULL,
            model_market_home_gap DOUBLE PRECISION,
            model_market_draw_gap DOUBLE PRECISION,
            model_market_away_gap DOUBLE PRECISION
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {scoreline_analysis_table} (
            match_no BIGINT NOT NULL,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT,
            away_team_zh TEXT,
            raw_home_expected_goals DOUBLE PRECISION,
            raw_away_expected_goals DOUBLE PRECISION,
            home_expected_goals DOUBLE PRECISION NOT NULL,
            away_expected_goals DOUBLE PRECISION NOT NULL,
            home_lineup_goal_factor DOUBLE PRECISION,
            away_lineup_goal_factor DOUBLE PRECISION,
            home_lineup_log_adjustment DOUBLE PRECISION,
            away_lineup_log_adjustment DOUBLE PRECISION,
            home_lineup_status TEXT,
            away_lineup_status TEXT,
            home_formation TEXT,
            away_formation TEXT,
            dixon_coles_rho DOUBLE PRECISION NOT NULL,
            score_home_win_probability DOUBLE PRECISION NOT NULL,
            score_draw_probability DOUBLE PRECISION NOT NULL,
            score_away_win_probability DOUBLE PRECISION NOT NULL,
            over_2_5_probability DOUBLE PRECISION NOT NULL,
            under_2_5_probability DOUBLE PRECISION NOT NULL,
            both_teams_score_probability DOUBLE PRECISION NOT NULL,
            clean_sheet_home_probability DOUBLE PRECISION NOT NULL,
            clean_sheet_away_probability DOUBLE PRECISION NOT NULL,
            scoreline_rank INTEGER NOT NULL,
            scoreline TEXT NOT NULL,
            scoreline_probability DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (match_no, scoreline_rank)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {scoreline_value_bets_table} (
            match_no BIGINT NOT NULL,
            stage TEXT NOT NULL,
            group_name TEXT,
            date_et DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_team_zh TEXT,
            away_team_zh TEXT,
            scoreline_rank INTEGER NOT NULL,
            scoreline TEXT NOT NULL,
            model_probability DOUBLE PRECISION NOT NULL,
            model_fair_odds DOUBLE PRECISION NOT NULL,
            best_decimal_odds DOUBLE PRECISION,
            average_decimal_odds DOUBLE PRECISION,
            raw_market_implied_probability DOUBLE PRECISION,
            listed_score_fair_probability DOUBLE PRECISION,
            listed_score_market_overround_proxy DOUBLE PRECISION,
            market_edge DOUBLE PRECISION,
            kelly_fraction DOUBLE PRECISION NOT NULL,
            has_score_odds BOOLEAN NOT NULL,
            value_signal TEXT NOT NULL,
            bookmaker_count BIGINT,
            source_names TEXT,
            source_urls TEXT,
            source_match_ids TEXT,
            latest_fetched_at TIMESTAMPTZ,
            PRIMARY KEY (match_no, scoreline_rank)
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
        CREATE INDEX IF NOT EXISTS idx_team_goal_form_as_of_date
        ON {team_goal_form_table} (as_of_date)
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
        CREATE INDEX IF NOT EXISTS idx_odds_raw_api_responses_payload_type
        ON {odds_raw_api_responses_table} (payload_type)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_market_odds_snapshots_event
        ON {market_odds_snapshots_table} (event_id)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_match_odds_features_teams
        ON {match_odds_features_table} (home_team, away_team)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_historical_market_odds_snapshots_event
        ON {historical_market_odds_snapshots_table} (event_id)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_historical_match_odds_features_teams
        ON {historical_match_odds_features_table} (home_team, away_team)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_predicted_lineups_match
        ON {predicted_lineups_table} (match_no)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_predicted_lineups_team
        ON {predicted_lineups_table} (team_name)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_score_odds_snapshots_match
        ON {score_odds_snapshots_table} (match_no)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_score_odds_snapshots_source_match
        ON {score_odds_snapshots_table} (source_name, source_match_id)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_score_odds_history_source_match
        ON {score_odds_history_table} (source_name, source_match_id, fetched_at)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_score_odds_features_match
        ON {score_odds_features_table} (match_no)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_score_odds_collection_status_status
        ON {score_odds_collection_status_table} (status)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_score_odds_collection_status_source_match
        ON {score_odds_collection_status_table} (source_name, source_match_id)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_enhanced_predictions_group
        ON {enhanced_predictions_table} (group_name)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_scoreline_analysis_match
        ON {scoreline_analysis_table} (match_no)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_scoreline_value_bets_signal
        ON {scoreline_value_bets_table} (value_signal)
        """,
    )


def create_schema_objects(connection: psycopg.Connection, schema: str) -> None:
    with connection.cursor() as cursor:
        statements = postgres_schema_sql(schema)
        cursor.execute(statements[0])
        for table in reversed(MANAGED_POSTGRES_TABLES):
            cursor.execute(f"DROP TABLE IF EXISTS {qualified_table(schema, table)} CASCADE")
        for statement in statements[1:]:
            cursor.execute(statement)
    connection.commit()


def read_json_file(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def read_raw_metadata(path: Path) -> dict[str, object]:
    candidates = [
        path.with_suffix(".meta.json"),
        Path(f"{path}.meta.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            metadata = read_json_file(candidate)
            return metadata if isinstance(metadata, dict) else {}
    return {}


def build_raw_odds_api_response_frame(raw_odds_dir: Path = RAW_ODDS_DIR) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if not raw_odds_dir.exists():
        return pd.DataFrame()

    payload_paths = sorted(
        path
        for path in raw_odds_dir.rglob("*.json")
        if not path.name.endswith(".meta.json")
    )
    for path in payload_paths:
        payload = read_json_file(path)
        metadata = read_raw_metadata(path)
        relative_path = path.relative_to(raw_odds_dir).as_posix()
        name_parts = path.name.split("__")
        rows.append(
            {
                "source_file": relative_path,
                "source_path": str(path),
                "payload_type": name_parts[0] if name_parts else "unknown",
                "sport_key": name_parts[1] if len(name_parts) > 1 else None,
                "fetched_at": metadata.get("fetched_at"),
                "file_size_bytes": path.stat().st_size,
                "payload_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                "metadata_json": json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["fetched_at"] = pd.to_datetime(frame["fetched_at"], utc=True, errors="coerce")
    return frame.sort_values("source_file").reset_index(drop=True)


def read_optional_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def read_optional_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def normalize_nullable_integer_columns(
    frame: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    if frame.empty:
        return frame
    normalized = frame.copy()
    for column in columns:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(
                normalized[column],
                errors="coerce",
            ).astype("Int64")
    return normalized


def read_enhanced_predictions_frame() -> pd.DataFrame:
    return normalize_nullable_integer_columns(
        read_optional_csv(ENHANCED_PREDICTIONS_PATH),
        ["bookmaker_count"],
    )


def read_scoreline_value_bets_frame() -> pd.DataFrame:
    return normalize_nullable_integer_columns(
        read_optional_csv(SCORELINE_VALUE_BETS_PATH),
        ["scoreline_rank", "bookmaker_count"],
    )


def read_processed_frames() -> dict[str, pd.DataFrame]:
    baseline_predictions = read_optional_csv(BASELINE_PREDICTIONS_PATH)
    return {
        "matches": pd.read_parquet(MATCHES_PATH),
        "teams": pd.read_parquet(TEAMS_PATH),
        "ratings": pd.read_parquet(RATINGS_PATH),
        "fixtures_2026": pd.read_parquet(FIXTURES_PATH),
        "baseline_predictions": baseline_predictions,
        "fifa_rankings_2026": pd.read_parquet(FIFA_RANKINGS_PATH),
        "squads_2026": pd.read_parquet(SQUADS_2026_PATH),
        "world_cup_teams_2026": pd.read_parquet(WORLD_CUP_TEAMS_2026_PATH),
        "team_goal_form_features": pd.read_parquet(TEAM_GOAL_FORM_FEATURES_PATH),
        "match_feature_store_2026": pd.read_parquet(MATCH_FEATURE_STORE_2026_PATH),
        "historical_match_feature_store": pd.read_parquet(HISTORICAL_MATCH_FEATURE_STORE_PATH),
        "odds_raw_api_responses": build_raw_odds_api_response_frame(),
        "market_odds_snapshots": read_optional_parquet(MARKET_ODDS_SNAPSHOTS_PATH),
        "match_odds_features": read_optional_parquet(MATCH_ODDS_FEATURES_PATH),
        "historical_market_odds_snapshots": read_optional_parquet(
            HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH
        ),
        "historical_match_odds_features": read_optional_parquet(
            HISTORICAL_MATCH_ODDS_FEATURES_PATH
        ),
        "predicted_lineups": read_optional_parquet(PREDICTED_LINEUPS_PATH),
        "score_odds_snapshots": read_optional_parquet(SCORE_ODDS_SNAPSHOTS_PATH),
        "score_odds_history": read_optional_parquet(SCORE_ODDS_HISTORY_PATH),
        "score_odds_features": read_optional_parquet(SCORE_ODDS_FEATURES_PATH),
        "score_odds_collection_status": read_optional_parquet(
            SCORE_ODDS_COLLECTION_STATUS_PATH
        ),
        "enhanced_predictions": read_enhanced_predictions_frame(),
        "scoreline_analysis": read_optional_csv(SCORELINE_ANALYSIS_PATH),
        "scoreline_value_bets": read_scoreline_value_bets_frame(),
    }


def dataframe_to_copy_buffer(frame: pd.DataFrame, columns: list[str]) -> io.StringIO:
    normalized = frame.copy()
    for column in columns:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized = normalized[columns].copy()
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
    with connection.cursor() as cursor:
        for table in MANAGED_POSTGRES_TABLES:
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
