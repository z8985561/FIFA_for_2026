from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .project_paths import (
    HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH,
    HISTORICAL_MATCH_ODDS_FEATURES_PATH,
    MARKET_ODDS_SNAPSHOTS_PATH,
    MATCH_ODDS_FEATURES_PATH,
    RAW_HISTORICAL_ODDS_DIR,
    RAW_ODDS_DIR,
    ensure_project_directories,
)
from .team_names import normalize_team_name

ODDS_FILE_GLOB = "odds__soccer_fifa_world_cup__*.json"
META_FILE_SUFFIX = ".meta.json"
H2H_MARKET_KEY = "h2h"
DRAW_OUTCOME_NAME = "Draw"
MANUAL_ODDS_REQUIRED_COLUMNS = [
    "match_date",
    "home_team",
    "away_team",
    "home_win_odds",
    "draw_odds",
    "away_win_odds",
]


@dataclass(frozen=True)
class OddsPipelineOutputs:
    market_odds_snapshots_path: str
    match_odds_features_path: str
    snapshot_rows: int
    feature_rows: int
    source_files: int


def discover_odds_files(raw_odds_dir: Path = RAW_ODDS_DIR) -> list[Path]:
    return sorted(
        path for path in raw_odds_dir.glob(ODDS_FILE_GLOB)
        if not path.name.endswith(META_FILE_SUFFIX)
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_meta(path: Path) -> dict[str, Any]:
    candidates = [
        path.with_suffix(".meta.json"),
        Path(f"{path}{META_FILE_SUFFIX}"),
    ]
    for meta_path in candidates:
        if meta_path.exists():
            meta = read_json(meta_path)
            return meta if isinstance(meta, dict) else {}
    return {}


def implied_probabilities_from_odds(
    home_win_odds: float,
    draw_odds: float,
    away_win_odds: float,
) -> tuple[float, float, float, float]:
    raw_home = 1.0 / float(home_win_odds)
    raw_draw = 1.0 / float(draw_odds)
    raw_away = 1.0 / float(away_win_odds)
    total = raw_home + raw_draw + raw_away
    overround = total - 1.0
    return (
        raw_home / total,
        raw_draw / total,
        raw_away / total,
        overround,
    )


def parse_h2h_outcomes(
    outcomes: list[dict[str, Any]],
    *,
    home_team: str,
    away_team: str,
) -> tuple[float, float, float] | None:
    prices: dict[str, float] = {}
    for outcome in outcomes:
        raw_name = outcome.get("name", outcome.get("outcome_name", ""))
        name = normalize_team_name(str(raw_name))
        price = outcome.get("price")
        if name and price is not None:
            prices[name] = float(price)

    if home_team not in prices or away_team not in prices or DRAW_OUTCOME_NAME not in prices:
        return None
    return prices[home_team], prices[DRAW_OUTCOME_NAME], prices[away_team]


def build_market_odds_snapshots(raw_odds_dir: Path = RAW_ODDS_DIR) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for odds_path in discover_odds_files(raw_odds_dir):
        payload = read_json(odds_path)
        meta = read_meta(odds_path)
        fetched_at = meta.get("fetched_at")
        request_label = meta.get("job", {}).get("label")
        request_markets = meta.get("job", {}).get("markets")
        request_regions = meta.get("job", {}).get("regions")

        if not isinstance(payload, list):
            continue

        for event in payload:
            home_team = normalize_team_name(str(event.get("home_team", "")))
            away_team = normalize_team_name(str(event.get("away_team", "")))
            if not home_team or not away_team:
                continue

            for bookmaker in event.get("bookmakers", []):
                bookmaker_key = str(bookmaker.get("key", ""))
                bookmaker_title = str(bookmaker.get("title", bookmaker_key))
                bookmaker_last_update = bookmaker.get("last_update")

                for market in bookmaker.get("markets", []):
                    market_key = str(market.get("key", ""))
                    market_last_update = market.get("last_update") or bookmaker_last_update
                    for outcome in market.get("outcomes", []):
                        outcome_name = normalize_team_name(str(outcome.get("name", "")))
                        price = outcome.get("price")
                        point = outcome.get("point")
                        if not outcome_name or price is None:
                            continue
                        rows.append(
                            {
                                "source_file": odds_path.name,
                                "request_label": request_label,
                                "request_markets": request_markets,
                                "request_regions": request_regions,
                                "fetched_at": fetched_at,
                                "event_id": str(event.get("id", "")),
                                "sport_key": str(event.get("sport_key", "")),
                                "sport_title": str(event.get("sport_title", "")),
                                "commence_time": event.get("commence_time"),
                                "home_team": home_team,
                                "away_team": away_team,
                                "bookmaker_key": bookmaker_key,
                                "bookmaker_title": bookmaker_title,
                                "bookmaker_last_update": bookmaker_last_update,
                                "market_key": market_key,
                                "market_last_update": market_last_update,
                                "outcome_name": outcome_name,
                                "price": float(price),
                                "point": float(point) if point is not None else None,
                            }
                        )

    snapshots = pd.DataFrame(rows)
    if snapshots.empty:
        return snapshots

    datetime_columns = [
        "fetched_at",
        "commence_time",
        "bookmaker_last_update",
        "market_last_update",
    ]
    for column in datetime_columns:
        snapshots[column] = pd.to_datetime(snapshots[column], utc=True, errors="coerce")

    return snapshots.sort_values(
        ["commence_time", "event_id", "bookmaker_key", "market_key", "outcome_name", "fetched_at"]
    ).reset_index(drop=True)


def manual_csv_commence_time(row: pd.Series) -> pd.Timestamp:
    if pd.notna(row.get("commence_time")):
        return pd.to_datetime(row["commence_time"], utc=True, errors="raise")
    return pd.to_datetime(row["match_date"], utc=True, errors="raise")


def validate_manual_odds_csv(frame: pd.DataFrame, source_path: Path) -> None:
    missing = [
        column for column in MANUAL_ODDS_REQUIRED_COLUMNS
        if column not in frame.columns
    ]
    if missing:
        raise ValueError(f"{source_path} is missing required columns: {missing}")


def build_market_odds_snapshots_from_manual_csv(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    if frame.empty:
        return pd.DataFrame()
    validate_manual_odds_csv(frame, csv_path)

    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        home_team = normalize_team_name(str(row["home_team"]))
        away_team = normalize_team_name(str(row["away_team"]))
        commence_time = manual_csv_commence_time(row)
        event_id = str(
            row.get("event_id")
            or f"manual-{commence_time.date()}-{home_team}-{away_team}"
        )
        bookmaker_key = str(row.get("bookmaker_key") or "manual")
        bookmaker_title = str(row.get("bookmaker_title") or bookmaker_key)
        fetched_at = pd.to_datetime(
            row.get("fetched_at", commence_time),
            utc=True,
            errors="coerce",
        )
        bookmaker_last_update = pd.to_datetime(
            row.get("bookmaker_last_update", fetched_at),
            utc=True,
            errors="coerce",
        )
        market_last_update = pd.to_datetime(
            row.get("market_last_update", bookmaker_last_update),
            utc=True,
            errors="coerce",
        )
        prices = [
            (home_team, row["home_win_odds"]),
            (DRAW_OUTCOME_NAME, row["draw_odds"]),
            (away_team, row["away_win_odds"]),
        ]
        for outcome_name, price in prices:
            rows.append(
                {
                    "source_file": csv_path.name,
                    "request_label": "manual_csv",
                    "request_markets": H2H_MARKET_KEY,
                    "request_regions": row.get("region"),
                    "fetched_at": fetched_at,
                    "event_id": event_id,
                    "sport_key": "soccer_fifa_world_cup",
                    "sport_title": "FIFA World Cup",
                    "commence_time": commence_time,
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker_key": bookmaker_key,
                    "bookmaker_title": bookmaker_title,
                    "bookmaker_last_update": bookmaker_last_update,
                    "market_key": H2H_MARKET_KEY,
                    "market_last_update": market_last_update,
                    "outcome_name": outcome_name,
                    "price": float(price),
                    "point": None,
                }
            )

    snapshots = pd.DataFrame(rows)
    return snapshots.sort_values(
        ["commence_time", "event_id", "bookmaker_key", "market_key", "outcome_name", "fetched_at"]
    ).reset_index(drop=True)


def combine_market_odds_snapshots(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty_frames = [frame for frame in frames if not frame.empty]
    if not non_empty_frames:
        return pd.DataFrame()
    return pd.concat(non_empty_frames, ignore_index=True).sort_values(
        ["commence_time", "event_id", "bookmaker_key", "market_key", "outcome_name", "fetched_at"]
    ).reset_index(drop=True)


def latest_market_rows(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(
        [
            "event_id",
            "bookmaker_key",
            "market_key",
            "outcome_name",
            "fetched_at",
            "market_last_update",
        ]
    )
    return ordered.groupby(
        ["event_id", "bookmaker_key", "market_key", "outcome_name"],
        as_index=False,
        sort=False,
    ).tail(1)


def build_match_odds_features(market_odds_snapshots: pd.DataFrame) -> pd.DataFrame:
    if market_odds_snapshots.empty:
        return pd.DataFrame()

    latest = latest_market_rows(market_odds_snapshots)
    latest_h2h = latest.loc[latest["market_key"].eq(H2H_MARKET_KEY)].copy()
    if latest_h2h.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for (event_id, bookmaker_key), group in latest_h2h.groupby(
        ["event_id", "bookmaker_key"],
        sort=True,
    ):
        sample = group.iloc[0]
        parsed = parse_h2h_outcomes(
            group[["outcome_name", "price"]].to_dict(orient="records"),
            home_team=str(sample["home_team"]),
            away_team=str(sample["away_team"]),
        )
        if parsed is None:
            continue

        home_win_odds, draw_odds, away_win_odds = parsed
        (
            home_win_implied_probability,
            draw_implied_probability,
            away_win_implied_probability,
            market_overround,
        ) = implied_probabilities_from_odds(home_win_odds, draw_odds, away_win_odds)

        rows.append(
            {
                "event_id": event_id,
                "bookmaker_key": bookmaker_key,
                "bookmaker_title": str(sample["bookmaker_title"]),
                "commence_time": sample["commence_time"],
                "home_team": str(sample["home_team"]),
                "away_team": str(sample["away_team"]),
                "bookmaker_last_update": sample["bookmaker_last_update"],
                "market_last_update": sample["market_last_update"],
                "fetched_at": sample["fetched_at"],
                "home_win_odds": home_win_odds,
                "draw_odds": draw_odds,
                "away_win_odds": away_win_odds,
                "home_win_implied_probability": home_win_implied_probability,
                "draw_implied_probability": draw_implied_probability,
                "away_win_implied_probability": away_win_implied_probability,
                "market_overround": market_overround,
            }
        )

    bookmaker_features = pd.DataFrame(rows)
    if bookmaker_features.empty:
        return bookmaker_features

    consensus = bookmaker_features.groupby(
        ["event_id", "commence_time", "home_team", "away_team"],
        as_index=False,
    ).agg(
        consensus_home_win_probability=("home_win_implied_probability", "mean"),
        consensus_draw_probability=("draw_implied_probability", "mean"),
        consensus_away_win_probability=("away_win_implied_probability", "mean"),
        avg_market_overround=("market_overround", "mean"),
        min_market_overround=("market_overround", "min"),
        max_market_overround=("market_overround", "max"),
        bookmaker_count=("bookmaker_key", "nunique"),
        latest_bookmaker_update=("bookmaker_last_update", "max"),
        latest_market_update=("market_last_update", "max"),
        latest_fetched_at=("fetched_at", "max"),
    )

    consensus["consensus_fair_probability_sum"] = (
        consensus["consensus_home_win_probability"]
        + consensus["consensus_draw_probability"]
        + consensus["consensus_away_win_probability"]
    )
    consensus["market_entropy"] = -(
        consensus["consensus_home_win_probability"]
        * np.log(consensus["consensus_home_win_probability"].clip(lower=1e-12))
        + consensus["consensus_draw_probability"]
        * np.log(consensus["consensus_draw_probability"].clip(lower=1e-12))
        + consensus["consensus_away_win_probability"]
        * np.log(consensus["consensus_away_win_probability"].clip(lower=1e-12))
    )
    consensus["favorite_probability"] = consensus[
        [
            "consensus_home_win_probability",
            "consensus_draw_probability",
            "consensus_away_win_probability",
        ]
    ].max(axis=1)
    consensus["favorite_outcome"] = consensus[
        [
            "consensus_home_win_probability",
            "consensus_draw_probability",
            "consensus_away_win_probability",
        ]
    ].idxmax(axis=1).str.replace("consensus_", "", regex=False).str.replace(
        "_probability",
        "",
        regex=False,
    )
    return consensus.sort_values(["commence_time", "event_id"]).reset_index(drop=True)


def prepare_odds_features(
    raw_odds_dir: Path = RAW_ODDS_DIR,
    *,
    market_odds_snapshots_path: Path = MARKET_ODDS_SNAPSHOTS_PATH,
    match_odds_features_path: Path = MATCH_ODDS_FEATURES_PATH,
    manual_csv_path: Path | None = None,
) -> OddsPipelineOutputs:
    ensure_project_directories()

    frames = [build_market_odds_snapshots(raw_odds_dir)]
    if manual_csv_path is not None and manual_csv_path.exists():
        frames.append(build_market_odds_snapshots_from_manual_csv(manual_csv_path))
    market_odds_snapshots = combine_market_odds_snapshots(frames)
    match_odds_features = build_match_odds_features(market_odds_snapshots)

    market_odds_snapshots.to_parquet(market_odds_snapshots_path, index=False)
    match_odds_features.to_parquet(match_odds_features_path, index=False)

    return OddsPipelineOutputs(
        market_odds_snapshots_path=str(market_odds_snapshots_path),
        match_odds_features_path=str(match_odds_features_path),
        snapshot_rows=len(market_odds_snapshots),
        feature_rows=len(match_odds_features),
        source_files=len(discover_odds_files(raw_odds_dir))
        + int(manual_csv_path is not None and manual_csv_path.exists()),
    )


def prepare_historical_odds_features(
    raw_odds_dir: Path = RAW_HISTORICAL_ODDS_DIR,
    *,
    manual_csv_path: Path | None = None,
) -> OddsPipelineOutputs:
    return prepare_odds_features(
        raw_odds_dir=raw_odds_dir,
        market_odds_snapshots_path=HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH,
        match_odds_features_path=HISTORICAL_MATCH_ODDS_FEATURES_PATH,
        manual_csv_path=manual_csv_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build processed odds snapshots and features.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_ODDS_DIR)
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Write outputs to the historical odds feature paths.",
    )
    parser.add_argument(
        "--manual-csv",
        type=Path,
        default=None,
        help="Optional manually curated 1X2 odds CSV to merge into the pipeline.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = (
        prepare_historical_odds_features(
            raw_odds_dir=args.raw_dir,
            manual_csv_path=args.manual_csv,
        )
        if args.historical
        else prepare_odds_features(
            raw_odds_dir=args.raw_dir,
            manual_csv_path=args.manual_csv,
        )
    )
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
