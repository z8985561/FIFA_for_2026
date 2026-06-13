from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import requests

from .project_paths import (
    FIXTURES_PATH,
    WANGYI_COACHES_2026_PATH,
    WANGYI_SQUAD_STATS_2026_PATH,
    ensure_project_directories,
)
from .team_names import normalize_team_name

BASE_URL = "https://gw.m.163.com/base/worldCup/qatar"
REQUEST_TIMEOUT = 10
MAX_WORKERS = 8
SUSPENSION_RED_CARD_THRESHOLD = 1
SUSPENSION_YELLOW_CARD_THRESHOLD = 2
EXPECTED_SQUAD_SIZE = 26


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"API error {data.get('code')}: {data.get('message')} - {url}")
    return data["data"]


def fetch_all_team_ids() -> list[dict[str, Any]]:
    """Fetch all qualified teams from the Wangyi schedule endpoint."""
    data = _get("schedule/groupByStage")
    teams: list[dict[str, Any]] = []
    seen: set[int] = set()
    for group in data.get("stageScheduleList", []):
        for team in group.get("teamList", []):
            team_id = int(team["teamId"])
            if team_id in seen:
                continue
            seen.add(team_id)
            raw_team_name = str(team["name"]).strip()
            teams.append(
                {
                    "team_id": team_id,
                    "team_name": normalize_team_name(raw_team_name),
                }
            )
    return teams


def fetch_team_data(team_id: int, team_name: str) -> dict[str, Any]:
    """Fetch coach and player stats for a single team."""
    lineup = _get("teamLineupInfo", {"teamId": team_id})
    manager = lineup.get("manager", {})

    coach_row: dict[str, Any] = {
        "team_id": team_id,
        "team_name": team_name,
        "manager_name_zh": (manager.get("nameZh") or "").strip() or None,
        "manager_name_en": manager.get("nameEn") or None,
        "manager_id": manager.get("playerId") or None,
    }

    player_rows: list[dict[str, Any]] = []
    position_map = {
        "goalkeeper": "GK",
        "back": "DF",
        "midfield": "MF",
        "forward": "FW",
    }
    for key, position in position_map.items():
        for player in lineup.get(key, []):
            yellow = int(player.get("yellowCards") or 0)
            red = int(player.get("redCards") or 0)
            player_rows.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "position": position,
                    "player_id": int(player.get("playerId") or 0),
                    "name_zh": (player.get("nameZh") or "").strip() or None,
                    "name_en": player.get("nameEn") or None,
                    "shirt_no": str(player.get("shirtNumber") or ""),
                    "age": int(player.get("age") or 0),
                    "goals": int(player.get("goals") or 0),
                    "assists": int(player.get("assists") or 0),
                    "yellow_cards": yellow,
                    "red_cards": red,
                    "is_suspended": (
                        red >= SUSPENSION_RED_CARD_THRESHOLD
                        or yellow >= SUSPENSION_YELLOW_CARD_THRESHOLD
                    ),
                }
            )

    return {"coach": coach_row, "players": player_rows}


def expected_fixture_teams() -> set[str]:
    if not FIXTURES_PATH.exists():
        return set()
    fixtures = pd.read_parquet(FIXTURES_PATH, columns=["home_team", "away_team"])
    teams = set(fixtures["home_team"]).union(set(fixtures["away_team"]))
    teams.discard("TBD")
    return {normalize_team_name(str(team)) for team in teams}


def validate_wangyi_outputs(
    coaches_df: pd.DataFrame,
    squads_df: pd.DataFrame,
    *,
    expected_teams: set[str] | None = None,
) -> list[str]:
    warnings: list[str] = []
    expected = expected_teams if expected_teams is not None else expected_fixture_teams()

    coach_teams = set(coaches_df["team_name"]) if "team_name" in coaches_df.columns else set()
    squad_teams = set(squads_df["team_name"]) if "team_name" in squads_df.columns else set()

    missing_in_coaches = sorted(expected - coach_teams)
    missing_in_squads = sorted(expected - squad_teams)
    unexpected_in_coaches = sorted(coach_teams - expected)
    unexpected_in_squads = sorted(squad_teams - expected)

    if missing_in_coaches:
        raise ValueError(f"Missing teams in wangyi coaches output: {missing_in_coaches}")
    if missing_in_squads:
        raise ValueError(f"Missing teams in wangyi squad output: {missing_in_squads}")
    if unexpected_in_coaches:
        raise ValueError(f"Unexpected teams in wangyi coaches output: {unexpected_in_coaches}")
    if unexpected_in_squads:
        raise ValueError(f"Unexpected teams in wangyi squad output: {unexpected_in_squads}")

    if squads_df.empty:
        return warnings

    duplicate_players = int(squads_df.duplicated(subset=["team_id", "player_id"]).sum())
    if duplicate_players:
        raise ValueError(f"Duplicate wangyi player rows detected: {duplicate_players}")

    squad_sizes = squads_df.groupby("team_name").size()
    abnormal_sizes = squad_sizes.loc[squad_sizes.ne(EXPECTED_SQUAD_SIZE)]
    if not abnormal_sizes.empty:
        warnings.append(
            "Abnormal squad sizes: "
            + ", ".join(f"{team}={size}" for team, size in abnormal_sizes.items())
        )

    return warnings


def collect(teams: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collect all teams concurrently and return coach/squad DataFrames."""
    coach_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(fetch_team_data, team["team_id"], team["team_name"]): team
            for team in teams
        }
        for future in as_completed(futures):
            team = futures[future]
            try:
                result = future.result()
                coach_rows.append(result["coach"])
                player_rows.extend(result["players"])
            except Exception as exc:
                errors.append(f"{team['team_name']} ({team['team_id']}): {exc}")

    if errors:
        print(f"[wangyi_pipeline] {len(errors)} team requests failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)

    fetched_at = datetime.now(UTC).isoformat()
    coaches_df = pd.DataFrame(coach_rows)
    squads_df = pd.DataFrame(player_rows)
    if not coaches_df.empty:
        coaches_df["fetched_at"] = fetched_at
    if not squads_df.empty:
        squads_df["fetched_at"] = fetched_at
    return coaches_df, squads_df


def save(coaches_df: pd.DataFrame, squads_df: pd.DataFrame) -> None:
    ensure_project_directories()
    coaches_df.to_parquet(WANGYI_COACHES_2026_PATH, index=False)
    squads_df.to_parquet(WANGYI_SQUAD_STATS_2026_PATH, index=False)
    print(f"coaches  -> {WANGYI_COACHES_2026_PATH} ({len(coaches_df)} rows)")
    print(f"squads   -> {WANGYI_SQUAD_STATS_2026_PATH} ({len(squads_df)} rows)")


def run_sync() -> dict[str, int]:
    """Sync Wangyi outputs into the dedicated Postgres tables."""
    from .postgres_sync import load_postgres_config, sync_wangyi_tables

    config = load_postgres_config()
    return sync_wangyi_tables(config)


def main() -> None:
    print("[wangyi_pipeline] Starting collection...")
    teams = fetch_all_team_ids()
    print(f"  discovered {len(teams)} teams")

    coaches_df, squads_df = collect(teams)
    print(f"  collected {len(coaches_df)} coaches and {len(squads_df)} players")

    suspended = int(squads_df["is_suspended"].sum()) if not squads_df.empty else 0
    print(f"  suspended players: {suspended}")

    warnings = validate_wangyi_outputs(coaches_df, squads_df)
    for warning in warnings:
        print(f"  warning: {warning}")

    save(coaches_df, squads_df)

    print("[wangyi_pipeline] Syncing to Postgres...")
    counts = run_sync()
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print("[wangyi_pipeline] Done.")


if __name__ == "__main__":
    main()
