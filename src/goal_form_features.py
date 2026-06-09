from __future__ import annotations

from dataclasses import asdict, dataclass

import duckdb
import pandas as pd

from .data_pipeline import prepare_research_data
from .project_paths import (
    DATABASE_PATH,
    MATCHES_PATH,
    TEAM_GOAL_FORM_FEATURES_PATH,
    ensure_project_directories,
)
from .schema import apply_schema

FORM_WINDOWS = (5, 10, 20)


@dataclass(frozen=True)
class GoalFormOutputs:
    goal_form_path: str
    database_path: str
    rows: int


def ensure_goal_form_inputs() -> None:
    if not MATCHES_PATH.exists():
        prepare_research_data()


def build_team_match_goal_rows(matches: pd.DataFrame) -> pd.DataFrame:
    home_rows = pd.DataFrame(
        {
            "match_id": matches["match_id"],
            "match_date": pd.to_datetime(matches["match_date"]),
            "team_name": matches["home_team"],
            "opponent_team": matches["away_team"],
            "goals_for": matches["home_score"].astype(float),
            "goals_against": matches["away_score"].astype(float),
            "competition_type": matches["competition_type"],
        }
    )
    away_rows = pd.DataFrame(
        {
            "match_id": matches["match_id"],
            "match_date": pd.to_datetime(matches["match_date"]),
            "team_name": matches["away_team"],
            "opponent_team": matches["home_team"],
            "goals_for": matches["away_score"].astype(float),
            "goals_against": matches["home_score"].astype(float),
            "competition_type": matches["competition_type"],
        }
    )
    rows = pd.concat([home_rows, away_rows], ignore_index=True)
    rows["goal_diff"] = rows["goals_for"] - rows["goals_against"]
    rows["clean_sheet"] = (rows["goals_against"] == 0).astype(float)
    rows["btts"] = ((rows["goals_for"] > 0) & (rows["goals_against"] > 0)).astype(float)
    rows["total_goals"] = rows["goals_for"] + rows["goals_against"]
    return rows.sort_values(["team_name", "match_date", "match_id"]).reset_index(drop=True)


def summarize_latest_team_goal_form(team_rows: pd.DataFrame) -> dict[str, object]:
    output: dict[str, object] = {
        "team_name": team_rows["team_name"].iloc[0],
        "as_of_date": team_rows["match_date"].max().date(),
        "matches_played": len(team_rows),
    }
    for window in FORM_WINDOWS:
        recent = team_rows.tail(window)
        output[f"goals_for_last_{window}"] = float(recent["goals_for"].mean())
        output[f"goals_against_last_{window}"] = float(recent["goals_against"].mean())
        output[f"goal_diff_last_{window}"] = float(recent["goal_diff"].mean())
        output[f"clean_sheet_rate_last_{window}"] = float(recent["clean_sheet"].mean())
        output[f"btts_rate_last_{window}"] = float(recent["btts"].mean())
        output[f"avg_total_goals_last_{window}"] = float(recent["total_goals"].mean())
    return output


def build_team_goal_form_features(matches: pd.DataFrame) -> pd.DataFrame:
    team_rows = build_team_match_goal_rows(matches)
    rows = [
        summarize_latest_team_goal_form(team_frame)
        for _, team_frame in team_rows.groupby("team_name", sort=True)
    ]
    return pd.DataFrame(rows)


def write_goal_form_table(goal_form: pd.DataFrame) -> None:
    connection = duckdb.connect(str(DATABASE_PATH))
    try:
        apply_schema(connection, table_names=("team_goal_form_features",))
        connection.register("goal_form_frame", goal_form)
        connection.execute(
            """
            INSERT INTO team_goal_form_features
            SELECT *
            FROM goal_form_frame
            """
        )
    finally:
        connection.close()


def prepare_goal_form_features() -> GoalFormOutputs:
    ensure_project_directories()
    ensure_goal_form_inputs()

    matches = pd.read_parquet(MATCHES_PATH)
    goal_form = build_team_goal_form_features(matches)
    goal_form.to_parquet(TEAM_GOAL_FORM_FEATURES_PATH, index=False)
    write_goal_form_table(goal_form)
    return GoalFormOutputs(
        goal_form_path=str(TEAM_GOAL_FORM_FEATURES_PATH),
        database_path=str(DATABASE_PATH),
        rows=len(goal_form),
    )


def main() -> None:
    outputs = prepare_goal_form_features()
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
