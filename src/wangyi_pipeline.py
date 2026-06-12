from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from .project_paths import (
    WANGYI_COACHES_2026_PATH,
    WANGYI_SQUAD_STATS_2026_PATH,
    ensure_project_directories,
)

BASE_URL = "https://gw.m.163.com/base/worldCup/qatar"
REQUEST_TIMEOUT = 10
MAX_WORKERS = 8

# 本届赛事停赛规则：1 张红牌 或 累计 2 张黄牌
SUSPENSION_RED_CARD_THRESHOLD = 1
SUSPENSION_YELLOW_CARD_THRESHOLD = 2


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"API error {data.get('code')}: {data.get('message')} — {url}")
    return data["data"]


def fetch_all_team_ids() -> list[dict[str, Any]]:
    """从小组赛程接口拿到全部 48 队的 teamId + name。"""
    data = _get("schedule/groupByStage")
    teams: list[dict[str, Any]] = []
    seen: set[int] = set()
    for group in data.get("stageScheduleList", []):
        for t in group.get("teamList", []):
            tid = int(t["teamId"])
            if tid not in seen:
                seen.add(tid)
                teams.append({"team_id": tid, "team_name": t["name"]})
    return teams


def fetch_team_data(team_id: int, team_name: str) -> dict[str, Any]:
    """并发任务单元：请求 teamLineupInfo，返回结构化结果。"""
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
    for key, pos_code in position_map.items():
        for p in lineup.get(key, []):
            yellow = int(p.get("yellowCards") or 0)
            red = int(p.get("redCards") or 0)
            is_suspended = (
                red >= SUSPENSION_RED_CARD_THRESHOLD
                or yellow >= SUSPENSION_YELLOW_CARD_THRESHOLD
            )
            player_rows.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "position": pos_code,
                    "player_id": int(p.get("playerId") or 0),
                    "name_zh": (p.get("nameZh") or "").strip() or None,
                    "name_en": p.get("nameEn") or None,
                    "shirt_no": str(p.get("shirtNumber") or ""),
                    "age": int(p.get("age") or 0),
                    "goals": int(p.get("goals") or 0),
                    "assists": int(p.get("assists") or 0),
                    "yellow_cards": yellow,
                    "red_cards": red,
                    "is_suspended": is_suspended,
                }
            )

    return {"coach": coach_row, "players": player_rows}


def collect(teams: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """并发采集所有队伍，返回 (coaches_df, squad_stats_df)。"""
    coach_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(fetch_team_data, t["team_id"], t["team_name"]): t
            for t in teams
        }
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                result = fut.result()
                coach_rows.append(result["coach"])
                player_rows.extend(result["players"])
            except Exception as exc:
                errors.append(f"{t['team_name']} ({t['team_id']}): {exc}")

    if errors:
        print(f"[wangyi_pipeline] {len(errors)} 个队伍采集失败:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)

    fetched_at = datetime.now(timezone.utc).isoformat()
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
    print(f"coaches  → {WANGYI_COACHES_2026_PATH}  ({len(coaches_df)} 行)")
    print(f"squads   → {WANGYI_SQUAD_STATS_2026_PATH}  ({len(squads_df)} 行)")


def run_sync() -> dict[str, int]:
    """触发 postgres_sync 对这两张表的覆盖写入，返回行数。"""
    from .postgres_sync import load_postgres_config, sync_wangyi_tables
    config = load_postgres_config()
    return sync_wangyi_tables(config)


def main() -> None:
    print("[wangyi_pipeline] 开始采集…")
    teams = fetch_all_team_ids()
    print(f"  发现 {len(teams)} 支参赛队伍")

    coaches_df, squads_df = collect(teams)
    print(f"  采集完成：{len(coaches_df)} 支队教练，{len(squads_df)} 名球员")

    suspended = squads_df["is_suspended"].sum() if not squads_df.empty else 0
    print(f"  当前停赛球员：{suspended} 人")

    save(coaches_df, squads_df)

    print("[wangyi_pipeline] 同步到 Postgres…")
    counts = run_sync()
    for table, cnt in counts.items():
        print(f"  {table}: {cnt} 行")
    print("[wangyi_pipeline] 完成。")


if __name__ == "__main__":
    main()
