from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 50.0


def classify_competition(tournament: str) -> str:
    name = tournament.lower()
    if "friendly" in name:
        return "friendly"
    if "world cup" in name:
        return "world_cup"
    if "nations league" in name:
        return "nations_league"
    if "qualif" in name:
        return "qualifier"
    if "cup" in name or "championship" in name:
        return "cup"
    return "other"


def classify_outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def expected_home_score(
    home_rating: float,
    away_rating: float,
    *,
    neutral: bool,
    config: EloConfig,
) -> float:
    adjusted_home_rating = home_rating if neutral else home_rating + config.home_advantage
    return 1.0 / (1.0 + 10.0 ** ((away_rating - adjusted_home_rating) / 400.0))


def observed_home_score(home_score: int, away_score: int) -> float:
    if home_score > away_score:
        return 1.0
    if home_score < away_score:
        return 0.0
    return 0.5


def build_elo_features(matches: pd.DataFrame, config: EloConfig | None = None) -> pd.DataFrame:
    config = config or EloConfig()
    working = matches.sort_values(["date", "home_team", "away_team"]).reset_index(drop=True).copy()

    ratings: dict[str, float] = {}
    last_played: dict[str, pd.Timestamp] = {}
    features: list[dict[str, object]] = []

    for match_id, row in enumerate(working.itertuples(index=False), start=1):
        home_team = row.home_team
        away_team = row.away_team
        match_date = pd.Timestamp(row.date)
        neutral = bool(row.neutral)

        pre_home = ratings.get(home_team, config.initial_rating)
        pre_away = ratings.get(away_team, config.initial_rating)
        expected_home = expected_home_score(
            pre_home,
            pre_away,
            neutral=neutral,
            config=config,
        )
        observed_home = observed_home_score(int(row.home_score), int(row.away_score))
        rating_delta = config.k_factor * (observed_home - expected_home)

        post_home = pre_home + rating_delta
        post_away = pre_away - rating_delta

        home_rest_days = (
            float((match_date - last_played[home_team]).days) if home_team in last_played else None
        )
        away_rest_days = (
            float((match_date - last_played[away_team]).days) if away_team in last_played else None
        )

        features.append(
            {
                "match_id": match_id,
                "match_date": match_date.date(),
                "competition_type": classify_competition(str(row.tournament)),
                "outcome": classify_outcome(int(row.home_score), int(row.away_score)),
                "pre_match_elo_home": pre_home,
                "pre_match_elo_away": pre_away,
                "elo_diff": pre_home - pre_away + (0.0 if neutral else config.home_advantage),
                "expected_home_win": expected_home,
                "home_rest_days": home_rest_days,
                "away_rest_days": away_rest_days,
                "post_match_elo_home": post_home,
                "post_match_elo_away": post_away,
            }
        )

        ratings[home_team] = post_home
        ratings[away_team] = post_away
        last_played[home_team] = match_date
        last_played[away_team] = match_date

    feature_frame = pd.DataFrame(features)
    return pd.concat([working, feature_frame], axis=1)


def build_latest_ratings(matches_with_features: pd.DataFrame) -> pd.DataFrame:
    home_rows = matches_with_features[["home_team", "match_date", "post_match_elo_home"]].rename(
        columns={
            "home_team": "team_name",
            "post_match_elo_home": "latest_elo",
        }
    )
    away_rows = matches_with_features[["away_team", "match_date", "post_match_elo_away"]].rename(
        columns={
            "away_team": "team_name",
            "post_match_elo_away": "latest_elo",
        }
    )

    combined = pd.concat([home_rows, away_rows], ignore_index=True)
    combined = combined.sort_values(["team_name", "match_date"]).reset_index(drop=True)

    latest = combined.groupby("team_name", as_index=False).agg(
        latest_match_date=("match_date", "max"),
        latest_elo=("latest_elo", "last"),
        matches_played=("match_date", "count"),
    )
    return latest
