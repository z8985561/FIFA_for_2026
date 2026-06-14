"""Pipeline to fetch World Cup match data from API-Football (v3).

Coverage (free tier, league=1, season=2026):
    - fixtures/events (goals, cards, substitutions)
    - fixtures/statistics (shots, passes, possession, etc.)
    - fixtures/lineups
    - predictions, odds

Usage:
    python -m src.apifootball_pipeline
    python -m src.apifootball_pipeline --season 2022 --limit 4  # historical
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import urllib.request

from src.project_paths import ensure_project_directories, PROCESSED_DATA_DIR

API_BASE = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1
DEFAULT_SEASON = 2026
REQUEST_TIMEOUT = 30

DATA_DIR = PROCESSED_DATA_DIR / "apifootball"
FIXTURES_PATH = DATA_DIR / "apifootball_fixtures.parquet"
STATISTICS_PATH = DATA_DIR / "apifootball_statistics.parquet"
EVENTS_PATH = DATA_DIR / "apifootball_events.parquet"


def _get_api_key() -> str:
    key = os.getenv("APIFOOTBALL_KEY", "726f3a4a22b67838ba140e4907b4f42c")
    return key


def _fetch(path: str, timeout: int = REQUEST_TIMEOUT) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={
        "x-apisports-key": _get_api_key(),
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _safe_int(value: Any) -> int | None:
    try:
        v = int(value)
        return v if v is not None else None
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


@dataclass(frozen=True)
class APIFootballOutputs:
    fixtures_path: str
    statistics_path: str
    events_path: str
    fixture_count: int
    statistics_count: int
    events_count: int
    fetched_at: str


def fetch_fixtures(
    *,
    season: int = DEFAULT_SEASON,
    league: int = WORLD_CUP_LEAGUE_ID,
) -> pd.DataFrame:
    payload = _fetch(f"/fixtures?league={league}&season={season}")
    rows: list[dict[str, Any]] = []
    for r in payload.get("response", []):
        f = r["fixture"]
        t = r["teams"]
        g = r["goals"]
        rows.append({
            "fixture_id": f["id"],
            "season": season,
            "match_date": _safe_str(f.get("date")),
            "status_short": _safe_str(f["status"]["short"]),
            "status_elapsed": _safe_int(f["status"].get("elapsed")),
            "home_team": _safe_str(t["home"]["name"]),
            "away_team": _safe_str(t["away"]["name"]),
            "home_team_id": _safe_int(t["home"]["id"]),
            "away_team_id": _safe_int(t["away"]["id"]),
            "home_score": _safe_int(g.get("home")),
            "away_score": _safe_int(g.get("away")),
            "venue_name": _safe_str(f["venue"].get("name")),
            "venue_city": _safe_str(f["venue"].get("city")),
            "round": _safe_str(r.get("league", {}).get("round")),
            "referee": _safe_str(f.get("referee")),
        })
    return pd.DataFrame(rows).sort_values("match_date").reset_index(drop=True)


def fetch_statistics(fixture_id: int) -> list[dict[str, Any]]:
    payload = _fetch(f"/fixtures/statistics?fixture={fixture_id}")
    rows: list[dict[str, Any]] = []
    for r in payload.get("response", []):
        team = r["team"]
        for s in r.get("statistics", []):
            rows.append({
                "fixture_id": fixture_id,
                "team_name": team["name"],
                "team_id": team["id"],
                "stat_type": s["type"],
                "stat_value": _safe_str(s.get("value")),
            })
    return rows


def fetch_events(fixture_id: int) -> list[dict[str, Any]]:
    payload = _fetch(f"/fixtures/events?fixture={fixture_id}")
    rows: list[dict[str, Any]] = []
    for r in payload.get("response", []):
        rows.append({
            "fixture_id": fixture_id,
            "elapsed": _safe_int(r.get("time", {}).get("elapsed")),
            "team_name": _safe_str(r["team"]["name"]),
            "player_name": _safe_str(r["player"]["name"]),
            "assist_name": _safe_str(r.get("assist", {}).get("name")),
            "event_type": _safe_str(r.get("type")),
            "event_detail": _safe_str(r.get("detail")),
            "event_comments": _safe_str(r.get("comments")),
        })
    return rows


def prepare_apifootball_data(
    *,
    season: int = DEFAULT_SEASON,
    league: int = WORLD_CUP_LEAGUE_ID,
    limit: int | None = None,
    skip_existing: bool = False,
) -> APIFootballOutputs:
    ensure_project_directories()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(UTC).isoformat()

    fixtures = fetch_fixtures(season=season, league=league)
    if fixtures.empty:
        return APIFootballOutputs(
            fixtures_path=str(FIXTURES_PATH),
            statistics_path=str(STATISTICS_PATH),
            events_path=str(EVENTS_PATH),
            fixture_count=0, statistics_count=0, events_count=0,
            fetched_at=fetched_at,
        )

    if skip_existing and FIXTURES_PATH.exists():
        existing = pd.read_parquet(FIXTURES_PATH)
        existing_ids = set(existing["fixture_id"])
        fixtures = fixtures[~fixtures["fixture_id"].isin(existing_ids)]

    if limit:
        fixtures = fixtures.head(limit)

    stats_rows: list[dict[str, Any]] = []
    events_rows: list[dict[str, Any]] = []
    for _, row in fixtures.iterrows():
        fid = int(row["fixture_id"])
        try:
            stats_rows.extend(fetch_statistics(fid))
        except Exception:
            pass
        try:
            events_rows.extend(fetch_events(fid))
        except Exception:
            pass

    fixtures.to_parquet(FIXTURES_PATH, index=False)
    pd.DataFrame(stats_rows).to_parquet(STATISTICS_PATH, index=False)
    pd.DataFrame(events_rows).to_parquet(EVENTS_PATH, index=False)

    return APIFootballOutputs(
        fixtures_path=str(FIXTURES_PATH),
        statistics_path=str(STATISTICS_PATH),
        events_path=str(EVENTS_PATH),
        fixture_count=len(fixtures),
        statistics_count=len(stats_rows),
        events_count=len(events_rows),
        fetched_at=fetched_at,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch World Cup data from API-Football")
    parser.add_argument("--season", type=int, default=DEFAULT_SEASON)
    parser.add_argument("--league", type=int, default=WORLD_CUP_LEAGUE_ID)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = prepare_apifootball_data(
        season=args.season, league=args.league,
        limit=args.limit, skip_existing=args.skip_existing,
    )
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
