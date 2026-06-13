"""从网易世界杯 API 拉取已完赛比赛的技战术数据。

数据来源:
    - 赛程 (mids): https://gw.m.163.com/base/worldCup/qatar/schedule
    - 技术统计:   https://gw.m.163.com/base/worldCup/qatar/tech/detail?mid={mid}

用法:
    python -m src.wangyi_tech_pipeline
    python -m src.wangyi_tech_pipeline --skip-existing  # 跳过已有 mid
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from .project_paths import (
    WANGYI_MATCH_PLAYERS_2026_PATH,
    WANGYI_MATCH_TECH_2026_PATH,
    ensure_project_directories,
)

SCHEDULE_URL = "https://gw.m.163.com/base/worldCup/qatar/schedule"
TECH_DETAIL_URL = "https://gw.m.163.com/base/worldCup/qatar/tech/detail?mid={mid}"
REQUEST_TIMEOUT = 30

# 网易 API 字段 → 统一列名
TECH_COLUMNS = [
    "mid",
    "match_date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "group_name",
    "home_coach",
    "away_coach",
    "home_possession",
    "away_possession",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_corners",
    "away_corners",
    "home_attacking_passes",
    "away_attacking_passes",
    "home_yellow_cards",
    "away_yellow_cards",
    "home_red_cards",
    "away_red_cards",
    "home_season_goals",
    "home_season_goals_conceded",
    "home_season_shots",
    "home_season_ontarget",
    "home_season_fouls",
    "home_season_yellow",
    "home_season_red",
    "away_season_goals",
    "away_season_goals_conceded",
    "away_season_shots",
    "away_season_ontarget",
    "away_season_fouls",
    "away_season_yellow",
    "away_season_red",
    "fetched_at",
]

PLAYER_COLUMNS = [
    "mid",
    "player_name",
    "player_id",
    "position",
    "side",
    "is_starting",
    "jersey_num",
    "events_json",
    "event_count",
    "has_goal",
    "has_yellow",
    "has_red",
]


@dataclass(frozen=True)
class WangyiTechOutputs:
    tech_path: str
    players_path: str
    tech_rows: int
    player_rows: int
    match_count: int
    fetched_at: str


def _fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> dict[str, Any]:
    import urllib.request

    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())  # type: ignore[no-any-return]


def fetch_finished_schedule() -> list[dict[str, Any]]:
    data = _fetch_json(SCHEDULE_URL)
    return data["data"]["finishScheduleList"]


def fetch_tech_detail(mid: int) -> dict[str, Any]:
    return _fetch_json(TECH_DETAIL_URL.format(mid=mid))["data"]


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _season_stat(stats: dict[str, Any], key: str) -> int:
    return _safe_int(stats.get(key, 0))


def build_tech_frame(finished: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    fetched_at = datetime.now(UTC).isoformat()

    for m in finished:
        mid = _safe_int(m["mid"])
        try:
            detail = fetch_tech_detail(mid)
        except Exception:
            continue

        ht = detail["homeTeamTech"]
        at = detail["awayTeamTech"]
        hst = detail.get("homeTeamSeasonTech", {})
        ast = detail.get("awayTeamSeasonTech", {})

        match_date_ms = m.get("date", 0)
        match_date = datetime.fromtimestamp(
            _safe_int(match_date_ms) / 1000, tz=UTC
        ).isoformat() if match_date_ms else None

        rows.append(
            {
                "mid": mid,
                "match_date": match_date,
                "home_team": m["home"],
                "away_team": m["away"],
                "home_score": _safe_int(m.get("homeScore", 0)),
                "away_score": _safe_int(m.get("awayScore", 0)),
                "group_name": m.get("groupName", ""),
                "home_coach": (detail.get("homeCoach") or "").strip(),
                "away_coach": (detail.get("awayCoach") or "").strip(),
                "home_possession": _safe_int(ht.get("possessionPercentage", 0)),
                "away_possession": _safe_int(at.get("possessionPercentage", 0)),
                "home_shots": _safe_int(ht.get("totalScoringAtt", 0)),
                "away_shots": _safe_int(at.get("totalScoringAtt", 0)),
                "home_shots_on_target": _safe_int(ht.get("ontargetScoringAtt", 0)),
                "away_shots_on_target": _safe_int(at.get("ontargetScoringAtt", 0)),
                "home_corners": _safe_int(ht.get("wonCorners", 0)),
                "away_corners": _safe_int(at.get("wonCorners", 0)),
                "home_attacking_passes": _safe_int(ht.get("totalAttackingPass", 0)),
                "away_attacking_passes": _safe_int(at.get("totalAttackingPass", 0)),
                "home_yellow_cards": _safe_int(ht.get("totalYelCard", 0)),
                "away_yellow_cards": _safe_int(at.get("totalYelCard", 0)),
                "home_red_cards": _safe_int(ht.get("totalRedCard", 0)),
                "away_red_cards": _safe_int(at.get("totalRedCard", 0)),
                "home_season_goals": _season_stat(hst, "goals"),
                "home_season_goals_conceded": _season_stat(hst, "goalsConceded"),
                "home_season_shots": _season_stat(hst, "totalScoringAtt"),
                "home_season_ontarget": _season_stat(hst, "ontargetScoringAtt"),
                "home_season_fouls": _season_stat(hst, "fouls"),
                "home_season_yellow": _season_stat(hst, "totalYelCard"),
                "home_season_red": _season_stat(hst, "totalRedCard"),
                "away_season_goals": _season_stat(ast, "goals"),
                "away_season_goals_conceded": _season_stat(ast, "goalsConceded"),
                "away_season_shots": _season_stat(ast, "totalScoringAtt"),
                "away_season_ontarget": _season_stat(ast, "ontargetScoringAtt"),
                "away_season_fouls": _season_stat(ast, "fouls"),
                "away_season_yellow": _season_stat(ast, "totalYelCard"),
                "away_season_red": _season_stat(ast, "totalRedCard"),
                "fetched_at": fetched_at,
            }
        )

    return pd.DataFrame(rows, columns=TECH_COLUMNS)


def build_players_frame(finished: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for m in finished:
        mid = _safe_int(m["mid"])
        try:
            detail = fetch_tech_detail(mid)
        except Exception:
            continue

        for p in detail.get("players", []):
            events = [
                {"type": e["type"], "time": e["time"]}
                for e in p.get("event", [])
                if e.get("type") in ("goal", "yellow", "red")
            ]
            rows.append(
                {
                    "mid": mid,
                    "player_name": str(p.get("player", "")),
                    "player_id": _safe_int(p.get("playerId", 0)),
                    "position": str(p.get("position", "")),
                    "side": _safe_int(p.get("side", 0)),
                    "is_starting": _safe_int(p.get("isStarting", 0)),
                    "jersey_num": _safe_int(p.get("jerseyNum", 0)),
                    "events_json": json.dumps(events, ensure_ascii=False) if events else None,
                    "event_count": len(events),
                    "has_goal": any(e["type"] == "goal" for e in events),
                    "has_yellow": any(e["type"] == "yellow" for e in events),
                    "has_red": any(e["type"] == "red" for e in events),
                }
            )

    return pd.DataFrame(rows, columns=PLAYER_COLUMNS)


def prepare_wangyi_tech(
    *,
    skip_existing: bool = False,
) -> WangyiTechOutputs:
    ensure_project_directories()
    fetched_at = datetime.now(UTC).isoformat()

    finished = fetch_finished_schedule()
    if not finished:
        return WangyiTechOutputs(
            tech_path=str(WANGYI_MATCH_TECH_2026_PATH),
            players_path=str(WANGYI_MATCH_PLAYERS_2026_PATH),
            tech_rows=0,
            player_rows=0,
            match_count=0,
            fetched_at=fetched_at,
        )

    if skip_existing and WANGYI_MATCH_TECH_2026_PATH.exists():
        existing_tech = pd.read_parquet(WANGYI_MATCH_TECH_2026_PATH)
        existing_mids = set(existing_tech["mid"].astype(int))
        finished = [m for m in finished if _safe_int(m["mid"]) not in existing_mids]

    tech_df = build_tech_frame(finished)
    players_df = build_players_frame(finished)

    tech_df.to_parquet(WANGYI_MATCH_TECH_2026_PATH, index=False)
    players_df.to_parquet(WANGYI_MATCH_PLAYERS_2026_PATH, index=False)

    return WangyiTechOutputs(
        tech_path=str(WANGYI_MATCH_TECH_2026_PATH),
        players_path=str(WANGYI_MATCH_PLAYERS_2026_PATH),
        tech_rows=len(tech_df),
        player_rows=len(players_df),
        match_count=len(finished),
        fetched_at=fetched_at,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从网易 API 拉取已完赛比赛的技战术数据"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="跳过已有 mid 的比赛",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = prepare_wangyi_tech(skip_existing=args.skip_existing)
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
