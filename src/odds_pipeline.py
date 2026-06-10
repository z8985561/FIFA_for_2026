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
) -> OddsPipelineOutputs:
    ensure_project_directories()

    market_odds_snapshots = build_market_odds_snapshots(raw_odds_dir)
    match_odds_features = build_match_odds_features(market_odds_snapshots)

    market_odds_snapshots.to_parquet(market_odds_snapshots_path, index=False)
    match_odds_features.to_parquet(match_odds_features_path, index=False)

    return OddsPipelineOutputs(
        market_odds_snapshots_path=str(market_odds_snapshots_path),
        match_odds_features_path=str(match_odds_features_path),
        snapshot_rows=len(market_odds_snapshots),
        feature_rows=len(match_odds_features),
        source_files=len(discover_odds_files(raw_odds_dir)),
    )


def prepare_historical_odds_features(
    raw_odds_dir: Path = RAW_HISTORICAL_ODDS_DIR,
) -> OddsPipelineOutputs:
    return prepare_odds_features(
        raw_odds_dir=raw_odds_dir,
        market_odds_snapshots_path=HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH,
        match_odds_features_path=HISTORICAL_MATCH_ODDS_FEATURES_PATH,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build processed odds snapshots and features.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_ODDS_DIR)
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Write outputs to the historical odds feature paths.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = (
        prepare_historical_odds_features(raw_odds_dir=args.raw_dir)
        if args.historical
        else prepare_odds_features(raw_odds_dir=args.raw_dir)
    )
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
