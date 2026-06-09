from __future__ import annotations

import io
from dataclasses import asdict, dataclass

import duckdb
import pandas as pd
import requests

from .elo import EloConfig, build_elo_features, build_latest_ratings
from .project_paths import (
    DATABASE_PATH,
    FIXTURES_2026_PATH,
    FIXTURES_PATH,
    MATCHES_PATH,
    RATINGS_PATH,
    RAW_HISTORY_PATH,
    TEAMS_PATH,
    ensure_project_directories,
)
from .schema import apply_schema
from .team_names import normalize_team_name

DEFAULT_HISTORY_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)


@dataclass(frozen=True)
class PipelineOutputs:
    raw_history_path: str
    matches_path: str
    teams_path: str
    ratings_path: str
    fixtures_path: str
    database_path: str


def download_historical_results(url: str = DEFAULT_HISTORY_URL) -> pd.DataFrame:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    RAW_HISTORY_PATH.write_bytes(response.content)
    return pd.read_csv(io.BytesIO(response.content))


def load_historical_results() -> pd.DataFrame:
    if RAW_HISTORY_PATH.exists():
        frame = pd.read_csv(RAW_HISTORY_PATH)
    else:
        frame = download_historical_results()

    frame = frame.dropna(subset=["home_team", "away_team", "home_score", "away_score"]).copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=False)
    frame["home_team"] = frame["home_team"].map(normalize_team_name)
    frame["away_team"] = frame["away_team"].map(normalize_team_name)
    frame["tournament"] = frame["tournament"].str.strip()
    frame["city"] = frame["city"].str.strip()
    frame["country"] = frame["country"].str.strip()
    frame["neutral"] = frame["neutral"].astype(str).str.upper().eq("TRUE")
    frame["home_score"] = frame["home_score"].astype(int)
    frame["away_score"] = frame["away_score"].astype(int)
    return frame


def build_teams_table(matches: pd.DataFrame) -> pd.DataFrame:
    home = matches[["date", "home_team"]].rename(columns={"home_team": "team_name"})
    away = matches[["date", "away_team"]].rename(columns={"away_team": "team_name"})
    combined = pd.concat([home, away], ignore_index=True)

    teams = combined.groupby("team_name", as_index=False).agg(
        first_match_date=("date", "min"),
        last_match_date=("date", "max"),
        total_matches=("date", "count"),
    )
    teams["first_match_date"] = teams["first_match_date"].dt.date
    teams["last_match_date"] = teams["last_match_date"].dt.date
    return teams.sort_values("team_name").reset_index(drop=True)


def stage_from_match_number(match_no: int) -> str:
    if 1 <= match_no <= 72:
        return "Group Stage"
    if 73 <= match_no <= 88:
        return "Round of 32"
    if 89 <= match_no <= 96:
        return "Round of 16"
    if 97 <= match_no <= 100:
        return "Quarter-Finals"
    if 101 <= match_no <= 102:
        return "Semi-Finals"
    if match_no == 103:
        return "Third Place"
    if match_no == 104:
        return "Final"
    return "Unknown"


def load_world_cup_fixtures() -> pd.DataFrame:
    fixtures = pd.read_csv(FIXTURES_2026_PATH)
    fixtures = fixtures.rename(columns={"group": "group_name"}).copy()
    fixtures["home_team"] = fixtures["home_team"].map(normalize_team_name)
    fixtures["away_team"] = fixtures["away_team"].map(normalize_team_name)
    fixtures["stage"] = fixtures["match_no"].map(stage_from_match_number)
    fixtures["date_et"] = pd.to_datetime(fixtures["date_et"]).dt.date
    fixtures["date_bj"] = pd.to_datetime(fixtures["date_bj"]).dt.date
    fixtures["neutral"] = True
    return fixtures


def write_duckdb_tables(
    matches: pd.DataFrame,
    teams: pd.DataFrame,
    ratings: pd.DataFrame,
    fixtures: pd.DataFrame,
) -> None:
    connection = duckdb.connect(str(DATABASE_PATH))
    try:
        apply_schema(connection)
        connection.register("matches_frame", matches)
        connection.register("teams_frame", teams)
        connection.register("ratings_frame", ratings)
        connection.register("fixtures_frame", fixtures)
        connection.execute(
            """
            INSERT INTO matches
            SELECT
                match_id,
                match_date,
                home_team,
                away_team,
                home_score,
                away_score,
                tournament,
                city,
                country,
                neutral,
                competition_type,
                outcome,
                pre_match_elo_home,
                pre_match_elo_away,
                elo_diff,
                expected_home_win,
                home_rest_days,
                away_rest_days,
                post_match_elo_home,
                post_match_elo_away
            FROM matches_frame
            """
        )
        connection.execute(
            """
            INSERT INTO teams
            SELECT
                team_name,
                first_match_date,
                last_match_date,
                total_matches
            FROM teams_frame
            """
        )
        connection.execute(
            """
            INSERT INTO ratings
            SELECT
                team_name,
                latest_match_date,
                latest_elo,
                matches_played
            FROM ratings_frame
            """
        )
        connection.execute(
            """
            INSERT INTO fixtures_2026
            SELECT
                match_no,
                stage,
                group_name,
                date_et,
                time_et,
                date_bj,
                time_bj,
                home_team,
                away_team,
                venue,
                city,
                neutral
            FROM fixtures_frame
            """
        )
    finally:
        connection.close()


def prepare_research_data() -> PipelineOutputs:
    ensure_project_directories()

    historical_results = load_historical_results()
    matches = build_elo_features(historical_results, config=EloConfig())
    teams = build_teams_table(matches)
    ratings = build_latest_ratings(matches)
    fixtures = load_world_cup_fixtures()

    matches.to_parquet(MATCHES_PATH, index=False)
    teams.to_parquet(TEAMS_PATH, index=False)
    ratings.to_parquet(RATINGS_PATH, index=False)
    fixtures.to_parquet(FIXTURES_PATH, index=False)

    write_duckdb_tables(matches, teams, ratings, fixtures)

    outputs = PipelineOutputs(
        raw_history_path=str(RAW_HISTORY_PATH),
        matches_path=str(MATCHES_PATH),
        teams_path=str(TEAMS_PATH),
        ratings_path=str(RATINGS_PATH),
        fixtures_path=str(FIXTURES_PATH),
        database_path=str(DATABASE_PATH),
    )
    return outputs


def main() -> None:
    outputs = prepare_research_data()
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
