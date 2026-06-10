from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from .project_paths import (
    FIXTURES_PATH,
    SPORTTERY_MARKET_ODDS_HISTORY_PATH,
    SPORTTERY_MARKET_ODDS_SNAPSHOTS_PATH,
    ensure_project_directories,
)
from .score_odds_pipeline import (
    DEFAULT_MATCH_LIMIT,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    SPORTTERY_BOOKMAKER_KEY,
    SPORTTERY_BOOKMAKER_TITLE,
    SPORTTERY_SOURCE_NAME,
    add_sporttery_match_ids_to_fixtures,
    discover_sporttery_match_metadata,
    fetch_sporttery_fixed_bonus,
    fixture_team_zh,
    score_odds_implied_probability,
    sporttery_match_id_for_fixture,
    sporttery_source_url,
)

SPORTTERY_LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")

SPORTTERY_MARKETS: dict[str, dict[str, Any]] = {
    "HAD": {
        "name_zh": "胜平负",
        "history_key": "hadList",
        "outcomes": {
            "h": ("home_win", "主胜"),
            "d": ("draw", "平"),
            "a": ("away_win", "客胜"),
        },
    },
    "HHAD": {
        "name_zh": "让球胜平负",
        "history_key": "hhadList",
        "outcomes": {
            "h": ("home_handicap_win", "让球主胜"),
            "d": ("handicap_draw", "让球平"),
            "a": ("away_handicap_win", "让球客胜"),
        },
    },
    "TTG": {
        "name_zh": "总进球",
        "history_key": "ttgList",
        "outcomes": {
            "s0": ("total_goals_0", "0球"),
            "s1": ("total_goals_1", "1球"),
            "s2": ("total_goals_2", "2球"),
            "s3": ("total_goals_3", "3球"),
            "s4": ("total_goals_4", "4球"),
            "s5": ("total_goals_5", "5球"),
            "s6": ("total_goals_6", "6球"),
            "s7": ("total_goals_7_plus", "7+球"),
        },
    },
    "HAFU": {
        "name_zh": "半全场",
        "history_key": "hafuList",
        "outcomes": {
            "hh": ("home_home", "胜胜"),
            "hd": ("home_draw", "胜平"),
            "ha": ("home_away", "胜负"),
            "dh": ("draw_home", "平胜"),
            "dd": ("draw_draw", "平平"),
            "da": ("draw_away", "平负"),
            "ah": ("away_home", "负胜"),
            "ad": ("away_draw", "负平"),
            "aa": ("away_away", "负负"),
        },
    },
}

OUTCOME_REVERSE_MAP = str.maketrans({"h": "a", "a": "h"})


@dataclass(frozen=True)
class SportteryMarketOddsPipelineOutputs:
    sporttery_market_odds_snapshots_path: str
    sporttery_market_odds_history_path: str | None
    snapshot_rows: int
    history_rows: int | None
    collected_matches: int
    collected_market_count: int


def parse_sporttery_update_at(row: dict[str, Any]) -> datetime | None:
    update_date = str(row.get("updateDate", "")).strip()
    update_time = str(row.get("updateTime", "")).strip()
    if not update_date or not update_time:
        return None
    try:
        local_dt = datetime.fromisoformat(f"{update_date}T{update_time}").replace(
            tzinfo=SPORTTERY_LOCAL_TIMEZONE
        )
    except ValueError:
        return None
    return local_dt.astimezone(UTC)


def latest_sporttery_market_row(
    payload: dict[str, Any],
    market_code: str,
) -> dict[str, Any] | None:
    market_config = SPORTTERY_MARKETS[market_code]
    rows = payload.get("value", {}).get("oddsHistory", {}).get(market_config["history_key"], [])
    if not isinstance(rows, list) or not rows:
        return None
    valid_rows = [row for row in rows if isinstance(row, dict)]
    if not valid_rows:
        return None
    return sorted(
        valid_rows,
        key=lambda row: f"{row.get('updateDate', '')} {row.get('updateTime', '')}",
    )[-1]


def normalized_goal_line(goal_line: object, *, source_home_away_reversed: bool) -> float | None:
    if goal_line in (None, "") or pd.isna(goal_line):
        return None
    try:
        line = float(goal_line)
    except (TypeError, ValueError):
        return None
    return -line if source_home_away_reversed else line


def local_outcome_field(
    source_field: str,
    *,
    market_code: str,
    source_home_away_reversed: bool,
) -> str:
    if not source_home_away_reversed or market_code == "TTG":
        return source_field
    return source_field.translate(OUTCOME_REVERSE_MAP)


def extract_sporttery_market_odds(
    payload: dict[str, Any],
    *,
    source_home_away_reversed: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for market_code, market_config in SPORTTERY_MARKETS.items():
        latest_row = latest_sporttery_market_row(payload, market_code)
        if latest_row is None:
            continue

        market_update_at = parse_sporttery_update_at(latest_row)
        goal_line = normalized_goal_line(
            latest_row.get("goalLine"),
            source_home_away_reversed=source_home_away_reversed,
        )
        for source_field in market_config["outcomes"]:
            raw_odds = latest_row.get(source_field)
            if raw_odds in (None, ""):
                continue
            try:
                decimal_odds = float(raw_odds)
            except (TypeError, ValueError):
                continue
            if decimal_odds <= 1.0:
                continue

            local_field = local_outcome_field(
                source_field,
                market_code=market_code,
                source_home_away_reversed=source_home_away_reversed,
            )
            outcome_code, outcome_name_zh = market_config["outcomes"][local_field]
            rows.append(
                {
                    "market_code": market_code,
                    "market_name_zh": market_config["name_zh"],
                    "outcome_code": outcome_code,
                    "outcome_name_zh": outcome_name_zh,
                    "source_outcome_field": source_field,
                    "source_decimal_odds": str(raw_odds),
                    "decimal_odds": decimal_odds,
                    "raw_implied_probability": score_odds_implied_probability(decimal_odds),
                    "goal_line": goal_line,
                    "market_update_at": market_update_at,
                }
            )
    return rows


def append_market_rows(
    snapshot_rows: list[dict[str, Any]],
    *,
    fixture: Any,
    extracted: list[dict[str, Any]],
    source_url: str,
    source_match_id: str,
    fetched_at: datetime,
    source_home_away_reversed: bool,
) -> None:
    home_team = str(fixture.home_team)
    away_team = str(fixture.away_team)
    for row in extracted:
        snapshot_rows.append(
            {
                "match_no": int(fixture.match_no),
                "stage": str(fixture.stage),
                "group_name": fixture.group_name,
                "date_et": pd.to_datetime(fixture.date_et).date(),
                "home_team": home_team,
                "away_team": away_team,
                "home_team_zh": fixture_team_zh(home_team),
                "away_team_zh": fixture_team_zh(away_team),
                "bookmaker_key": SPORTTERY_BOOKMAKER_KEY,
                "bookmaker_title": SPORTTERY_BOOKMAKER_TITLE,
                "source_name": SPORTTERY_SOURCE_NAME,
                "source_url": source_url,
                "source_match_id": source_match_id,
                "source_home_away_reversed": source_home_away_reversed,
                "fetched_at": fetched_at,
                **row,
            }
        )


def build_sporttery_market_odds_snapshots(
    fixtures: pd.DataFrame,
    *,
    match_limit: int = DEFAULT_MATCH_LIMIT,
    fetched_at: datetime | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    existing_sporttery_match_ids: set[str] | None = None,
) -> pd.DataFrame:
    fetched_at = fetched_at or datetime.now(UTC)
    fixture_rows = fixtures.sort_values(["date_et", "match_no"]).head(match_limit)
    existing_sporttery_match_ids = existing_sporttery_match_ids or set()
    snapshot_rows: list[dict[str, Any]] = []

    for fixture in fixture_rows.itertuples(index=False):
        fixture_series = pd.Series(fixture._asdict())
        sporttery_match_id = sporttery_match_id_for_fixture(fixture_series)
        if sporttery_match_id is None or sporttery_match_id in existing_sporttery_match_ids:
            continue

        source_home_away_reversed = bool(
            fixture_series.get("source_home_away_reversed", False)
        )
        try:
            payload = fetch_sporttery_fixed_bonus(
                sporttery_match_id,
                timeout_seconds=timeout_seconds,
            )
            extracted = extract_sporttery_market_odds(
                payload,
                source_home_away_reversed=source_home_away_reversed,
            )
        except Exception:
            continue
        append_market_rows(
            snapshot_rows,
            fixture=fixture,
            extracted=extracted,
            source_url=sporttery_source_url(sporttery_match_id),
            source_match_id=sporttery_match_id,
            fetched_at=fetched_at,
            source_home_away_reversed=source_home_away_reversed,
        )

    snapshots = pd.DataFrame(snapshot_rows)
    if snapshots.empty:
        return snapshots
    return snapshots.sort_values(
        ["match_no", "market_code", "outcome_code", "fetched_at"]
    ).reset_index(drop=True)


def merge_sporttery_market_odds_snapshots(
    previous_snapshots: pd.DataFrame,
    new_snapshots: pd.DataFrame,
) -> pd.DataFrame:
    if previous_snapshots.empty:
        return new_snapshots
    if new_snapshots.empty:
        return previous_snapshots
    combined = pd.concat([previous_snapshots, new_snapshots], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["match_no", "market_code", "outcome_code", "source_match_id"],
        keep="last",
    )
    return combined.sort_values(
        ["match_no", "market_code", "outcome_code", "fetched_at"]
    ).reset_index(drop=True)


def append_sporttery_market_odds_history(
    snapshots: pd.DataFrame,
    *,
    history_path=SPORTTERY_MARKET_ODDS_HISTORY_PATH,
) -> pd.DataFrame:
    previous_history = pd.read_parquet(history_path) if history_path.exists() else pd.DataFrame()
    if snapshots.empty:
        return previous_history
    if previous_history.empty:
        history = snapshots
    else:
        history = pd.concat([previous_history, snapshots], ignore_index=True)
    history = history.drop_duplicates(
        subset=[
            "match_no",
            "market_code",
            "outcome_code",
            "source_match_id",
            "market_update_at",
            "fetched_at",
        ],
        keep="last",
    )
    history = history.sort_values(
        ["match_no", "market_code", "outcome_code", "fetched_at"]
    ).reset_index(drop=True)
    history.to_parquet(history_path, index=False)
    return history


def prepare_sporttery_market_odds(
    *,
    fixtures_path=FIXTURES_PATH,
    match_limit: int = DEFAULT_MATCH_LIMIT,
    discover_sporttery: bool = True,
    skip_existing_sporttery: bool = False,
    append_history: bool = False,
    sporttery_market_odds_snapshots_path=SPORTTERY_MARKET_ODDS_SNAPSHOTS_PATH,
    sporttery_market_odds_history_path=SPORTTERY_MARKET_ODDS_HISTORY_PATH,
) -> SportteryMarketOddsPipelineOutputs:
    ensure_project_directories()
    fixtures = pd.read_parquet(fixtures_path)
    if discover_sporttery:
        try:
            sporttery_match_ids = discover_sporttery_match_metadata(fixtures)
        except Exception:
            sporttery_match_ids = {}
        fixtures = add_sporttery_match_ids_to_fixtures(fixtures, sporttery_match_ids)

    previous_snapshots = pd.DataFrame()
    existing_sporttery_match_ids: set[str] = set()
    if skip_existing_sporttery and sporttery_market_odds_snapshots_path.exists():
        previous_snapshots = pd.read_parquet(sporttery_market_odds_snapshots_path)
        if "source_match_id" in previous_snapshots.columns:
            existing_sporttery_match_ids = set(
                previous_snapshots["source_match_id"].dropna().astype(str)
            )

    snapshots = build_sporttery_market_odds_snapshots(
        fixtures,
        match_limit=match_limit,
        existing_sporttery_match_ids=existing_sporttery_match_ids,
    )
    if skip_existing_sporttery:
        snapshots = merge_sporttery_market_odds_snapshots(previous_snapshots, snapshots)

    snapshots.to_parquet(sporttery_market_odds_snapshots_path, index=False)
    history = (
        append_sporttery_market_odds_history(
            snapshots,
            history_path=sporttery_market_odds_history_path,
        )
        if append_history
        else None
    )

    return SportteryMarketOddsPipelineOutputs(
        sporttery_market_odds_snapshots_path=str(sporttery_market_odds_snapshots_path),
        sporttery_market_odds_history_path=(
            str(sporttery_market_odds_history_path) if append_history else None
        ),
        snapshot_rows=len(snapshots),
        history_rows=len(history) if history is not None else None,
        collected_matches=(
            int(snapshots["match_no"].nunique()) if not snapshots.empty else 0
        ),
        collected_market_count=(
            int(snapshots[["match_no", "market_code"]].drop_duplicates().shape[0])
            if not snapshots.empty
            else 0
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Sporttery fixed-bonus market odds beyond correct score."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_MATCH_LIMIT)
    parser.add_argument(
        "--skip-existing-sporttery",
        action="store_true",
        help="Skip Sporttery mids already present in the local market snapshot file.",
    )
    parser.add_argument(
        "--no-discover-sporttery",
        action="store_true",
        help="Disable Sporttery match-list discovery and use the built-in mid mapping only.",
    )
    parser.add_argument(
        "--append-history",
        action="store_true",
        help="Append this run's market snapshots to the historical snapshot file.",
    )
    args = parser.parse_args()

    outputs = prepare_sporttery_market_odds(
        match_limit=args.limit,
        discover_sporttery=not args.no_discover_sporttery,
        skip_existing_sporttery=args.skip_existing_sporttery,
        append_history=args.append_history,
    )
    print(asdict(outputs))


if __name__ == "__main__":
    main()
