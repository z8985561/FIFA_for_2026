from __future__ import annotations

from dataclasses import asdict, dataclass

import duckdb
import pandas as pd

from .elo import EloConfig, expected_home_score
from .project_paths import (
    DATABASE_PATH,
    FIXTURES_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    WORLD_CUP_TEAMS_2026_PATH,
    ensure_project_directories,
)
from .schema import apply_schema
from .world_cup_identity import prepare_world_cup_identity_data


@dataclass(frozen=True)
class FeatureStoreOutputs:
    match_feature_store_path: str
    database_path: str
    rows: int


def ensure_feature_inputs() -> None:
    if not FIXTURES_PATH.exists() or not WORLD_CUP_TEAMS_2026_PATH.exists():
        prepare_world_cup_identity_data()


def build_group_difficulty_features(team_profiles: pd.DataFrame) -> pd.DataFrame:
    grouped = team_profiles.groupby("group_name", as_index=False).agg(
        group_avg_elo=("latest_elo", "mean"),
        group_avg_fifa_rank=("fifa_rank", "mean"),
        group_elo_spread=("latest_elo", lambda values: values.max() - values.min()),
    )
    grouped = grouped.sort_values(
        ["group_avg_elo", "group_avg_fifa_rank"],
        ascending=[False, True],
    ).reset_index(drop=True)
    grouped["group_difficulty_rank"] = grouped.index + 1
    return grouped[
        [
            "group_name",
            "group_difficulty_rank",
            "group_avg_elo",
            "group_avg_fifa_rank",
            "group_elo_spread",
        ]
    ]


def add_team_profile_prefix(
    frame: pd.DataFrame,
    team_profiles: pd.DataFrame,
    team_column: str,
    prefix: str,
) -> pd.DataFrame:
    profile_columns = [
        "team_name",
        "confederation",
        "fifa_rank",
        "latest_elo",
        "squad_size",
        "squad_average_age",
        "squad_total_caps",
        "matches_played",
    ]
    renamed = team_profiles[profile_columns].rename(
        columns={
            "team_name": team_column,
            "confederation": f"{prefix}_confederation",
            "fifa_rank": f"{prefix}_fifa_rank",
            "latest_elo": f"{prefix}_latest_elo",
            "squad_size": f"{prefix}_squad_size",
            "squad_average_age": f"{prefix}_squad_average_age",
            "squad_total_caps": f"{prefix}_squad_total_caps",
            "matches_played": f"{prefix}_matches_played",
        }
    )
    return frame.merge(renamed, on=team_column, how="left")


def build_match_feature_store(
    fixtures: pd.DataFrame,
    team_profiles: pd.DataFrame,
) -> pd.DataFrame:
    config = EloConfig()
    known = fixtures[fixtures["home_team"].ne("TBD") & fixtures["away_team"].ne("TBD")].copy()

    features = add_team_profile_prefix(known, team_profiles, "home_team", "home")
    features = add_team_profile_prefix(features, team_profiles, "away_team", "away")
    features = features.merge(
        build_group_difficulty_features(team_profiles),
        on="group_name",
        how="left",
    )

    features["same_confederation"] = (
        features["home_confederation"] == features["away_confederation"]
    )
    features["home_rank_advantage"] = features["away_fifa_rank"] - features["home_fifa_rank"]
    features["elo_diff"] = features["home_latest_elo"] - features["away_latest_elo"]
    features["expected_home_win"] = features.apply(
        lambda row: expected_home_score(
            float(row["home_latest_elo"]),
            float(row["away_latest_elo"]),
            neutral=True,
            config=config,
        ),
        axis=1,
    )
    features["squad_size_diff"] = features["home_squad_size"] - features["away_squad_size"]
    features["squad_average_age_diff"] = (
        features["home_squad_average_age"] - features["away_squad_average_age"]
    )
    features["squad_total_caps_diff"] = (
        features["home_squad_total_caps"] - features["away_squad_total_caps"]
    )
    features["matches_played_diff"] = (
        features["home_matches_played"] - features["away_matches_played"]
    )
    features["neutral"] = True

    output_columns = [
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
    ]
    return features[output_columns].sort_values("match_no").reset_index(drop=True)


def write_feature_store_tables(match_features: pd.DataFrame) -> None:
    connection = duckdb.connect(str(DATABASE_PATH))
    try:
        apply_schema(connection, table_names=("match_feature_store_2026",))
        connection.register("match_feature_store_frame", match_features)
        connection.execute(
            """
            INSERT INTO match_feature_store_2026
            SELECT *
            FROM match_feature_store_frame
            """
        )
    finally:
        connection.close()


def prepare_match_feature_store() -> FeatureStoreOutputs:
    ensure_project_directories()
    ensure_feature_inputs()

    fixtures = pd.read_parquet(FIXTURES_PATH)
    team_profiles = pd.read_parquet(WORLD_CUP_TEAMS_2026_PATH)
    match_features = build_match_feature_store(fixtures, team_profiles)

    match_features.to_parquet(MATCH_FEATURE_STORE_2026_PATH, index=False)
    write_feature_store_tables(match_features)
    return FeatureStoreOutputs(
        match_feature_store_path=str(MATCH_FEATURE_STORE_2026_PATH),
        database_path=str(DATABASE_PATH),
        rows=len(match_features),
    )


def main() -> None:
    outputs = prepare_match_feature_store()
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
