from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .project_paths import (
    OFFICIAL_MATCH_RESULTS_2026_PATH,
    RAW_RESULTS_DIR,
    ensure_project_directories,
)
from .team_names import normalize_team_name

FIFA_API_BASE = "https://api.fifa.com/api/v3/calendar/matches"
FIFA_WORLD_CUP_2026_SEASON_ID = "285023"
DEFAULT_TIMEOUT_SECONDS = 30
FIFA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


@dataclass(frozen=True)
class OfficialResultsOutputs:
    raw_snapshot_path: str
    raw_metadata_path: str
    processed_results_path: str
    match_rows: int
    completed_matches: int
    fetched_at: str


def fifa_world_cup_results_url(season_id: str = FIFA_WORLD_CUP_2026_SEASON_ID) -> str:
    return f"{FIFA_API_BASE}?idSeason={season_id}"


def fetch_fifa_world_cup_results(
    *,
    season_id: str = FIFA_WORLD_CUP_2026_SEASON_ID,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], str]:
    url = fifa_world_cup_results_url(season_id)
    response = requests.get(url, headers=FIFA_HEADERS, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("FIFA results payload is not a JSON object")
    return payload, url


def _localized_name(values: Any) -> str | None:
    if not isinstance(values, list) or not values:
        return None
    for item in values:
        if isinstance(item, dict) and item.get("Locale") == "en-GB":
            description = item.get("Description")
            if description:
                return str(description)
    first = values[0]
    if isinstance(first, dict) and first.get("Description"):
        return str(first["Description"])
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text_or_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def build_official_results_frame(payload: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in payload.get("Results", []):
        if not isinstance(item, dict):
            continue

        home_team = normalize_team_name(
            _localized_name(item.get("Home", {}).get("TeamName")) or ""
        )
        away_team = normalize_team_name(
            _localized_name(item.get("Away", {}).get("TeamName")) or ""
        )
        if not home_team or not away_team:
            continue

        home_score = _int_or_none(item.get("HomeTeamScore"))
        away_score = _int_or_none(item.get("AwayTeamScore"))
        home_penalty_score = _int_or_none(item.get("HomeTeamPenaltyScore"))
        away_penalty_score = _int_or_none(item.get("AwayTeamPenaltyScore"))
        match_status = _int_or_none(item.get("MatchStatus"))
        completed = (
            home_score is not None
            and away_score is not None
            and match_status == 0
        )

        rows.append(
            {
                "match_no": _int_or_none(item.get("MatchNumber")),
                "match_id": _text_or_none(item.get("IdMatch")),
                "season_id": _text_or_none(item.get("IdSeason")),
                "stage_id": _text_or_none(item.get("IdStage")),
                "group_id": _text_or_none(item.get("IdGroup")),
                "stage_name": _localized_name(item.get("StageName")),
                "group_name": _localized_name(item.get("GroupName")),
                "date_utc": _text_or_none(item.get("Date")),
                "local_date_utc": _text_or_none(item.get("LocalDate")),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "home_penalty_score": home_penalty_score,
                "away_penalty_score": away_penalty_score,
                "winner_id": _text_or_none(item.get("Winner")),
                "match_status": match_status,
                "result_type": _int_or_none(item.get("ResultType")),
                "officiality_status": _int_or_none(item.get("OfficialityStatus")),
                "completed": completed,
                "stadium_name": _localized_name(item.get("Stadium", {}).get("Name")),
                "city_name": _localized_name(item.get("Stadium", {}).get("CityName")),
                "country_name": _localized_name(item.get("Stadium", {}).get("CountryName")),
                "attendance": _int_or_none(item.get("Attendance")),
                "last_period_update": _text_or_none(item.get("LastPeriodUpdate")),
                "match_report_url": _text_or_none(item.get("MatchReportUrl")),
                "source_name": "FIFA Official API",
                "source_url": fifa_world_cup_results_url(
                    _text_or_none(item.get("IdSeason")) or FIFA_WORLD_CUP_2026_SEASON_ID
                ),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    for column in ["date_utc", "local_date_utc", "last_period_update"]:
        frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")

    return frame.sort_values(["match_no", "date_utc"]).reset_index(drop=True)


def write_raw_snapshot(
    payload: dict[str, Any],
    *,
    request_url: str,
    fetched_at: datetime,
    raw_results_dir: Path = RAW_RESULTS_DIR,
    season_id: str = FIFA_WORLD_CUP_2026_SEASON_ID,
) -> tuple[Path, Path]:
    ensure_project_directories()
    timestamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    raw_path = raw_results_dir / f"fifa_results__{season_id}__{timestamp}.json"
    meta_path = raw_results_dir / f"fifa_results__{season_id}__{timestamp}.meta.json"

    raw_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(
            {
                "fetched_at": fetched_at.isoformat(),
                "season_id": season_id,
                "source_name": "FIFA Official API",
                "request_url": request_url,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return raw_path, meta_path


def prepare_official_results(
    *,
    season_id: str = FIFA_WORLD_CUP_2026_SEASON_ID,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    processed_results_path: Path = OFFICIAL_MATCH_RESULTS_2026_PATH,
) -> OfficialResultsOutputs:
    fetched_at = datetime.now(UTC)
    payload, request_url = fetch_fifa_world_cup_results(
        season_id=season_id,
        timeout_seconds=timeout_seconds,
    )
    raw_path, meta_path = write_raw_snapshot(
        payload,
        request_url=request_url,
        fetched_at=fetched_at,
        season_id=season_id,
    )
    frame = build_official_results_frame(payload)
    frame["fetched_at"] = fetched_at
    frame.to_parquet(processed_results_path, index=False)

    return OfficialResultsOutputs(
        raw_snapshot_path=str(raw_path),
        raw_metadata_path=str(meta_path),
        processed_results_path=str(processed_results_path),
        match_rows=len(frame),
        completed_matches=int(frame["completed"].fillna(False).sum()) if not frame.empty else 0,
        fetched_at=fetched_at.isoformat(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch official FIFA World Cup results.")
    parser.add_argument("--season-id", default=FIFA_WORLD_CUP_2026_SEASON_ID)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_official_results(
        season_id=args.season_id,
        timeout_seconds=args.timeout_seconds,
    )
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
