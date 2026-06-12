from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

HOME_WIN = "home_win"
DRAW = "draw"
AWAY_WIN = "away_win"


def scoreline_outcome_from_text(scoreline: str) -> str:
    home_goals_text, away_goals_text = str(scoreline).split("-", maxsplit=1)
    home_goals = int(home_goals_text)
    away_goals = int(away_goals_text)
    if home_goals > away_goals:
        return HOME_WIN
    if home_goals < away_goals:
        return AWAY_WIN
    return DRAW


def build_match_outcome_summary(scoreline_analysis: pd.DataFrame) -> pd.DataFrame:
    if scoreline_analysis.empty:
        return pd.DataFrame()

    columns = [
        "match_no",
        "home_team",
        "away_team",
        "home_team_zh",
        "away_team_zh",
        "score_home_win_probability",
        "score_draw_probability",
        "score_away_win_probability",
    ]
    summary = (
        scoreline_analysis[columns]
        .drop_duplicates(subset=["match_no"])
        .sort_values("match_no")
        .reset_index(drop=True)
        .copy()
    )
    home_probabilities = pd.to_numeric(
        summary["score_home_win_probability"],
        errors="coerce",
    ).fillna(0.0)
    away_probabilities = pd.to_numeric(
        summary["score_away_win_probability"],
        errors="coerce",
    ).fillna(0.0)
    summary["favorite_outcome"] = np.where(
        home_probabilities >= away_probabilities,
        HOME_WIN,
        AWAY_WIN,
    )
    summary["underdog_outcome"] = np.where(
        home_probabilities < away_probabilities,
        HOME_WIN,
        AWAY_WIN,
    )
    summary["favorite_probability"] = np.maximum(home_probabilities, away_probabilities)
    summary["underdog_probability"] = np.minimum(home_probabilities, away_probabilities)
    summary["upset_index"] = summary["underdog_probability"] * (
        1.0 - summary["favorite_probability"]
    )
    return summary


def build_two_leg_combo_pool(
    value_bets: pd.DataFrame,
    *,
    match_nos: list[int] | None = None,
    top_per_match: int = 8,
) -> pd.DataFrame:
    if value_bets.empty:
        return pd.DataFrame()

    subset = value_bets.loc[value_bets["has_score_odds"].fillna(False)].copy()
    if match_nos is not None:
        subset = subset.loc[subset["match_no"].isin(match_nos)].copy()
    subset = (
        subset.sort_values(
            ["match_no", "model_probability", "best_decimal_odds"],
            ascending=[True, False, False],
        )
        .groupby("match_no", sort=True)
        .head(top_per_match)
        .reset_index(drop=True)
    )

    rows: list[dict[str, object]] = []
    for left_match_no, right_match_no in combinations(sorted(subset["match_no"].unique()), 2):
        left_frame = subset.loc[subset["match_no"].eq(left_match_no)]
        right_frame = subset.loc[subset["match_no"].eq(right_match_no)]
        for left_row in left_frame.itertuples(index=False):
            for right_row in right_frame.itertuples(index=False):
                joint_probability = float(left_row.model_probability) * float(
                    right_row.model_probability
                )
                joint_odds = float(left_row.best_decimal_odds) * float(
                    right_row.best_decimal_odds
                )
                rows.append(
                    {
                        "leg_a_match_no": int(left_row.match_no),
                        "leg_a_home_team": left_row.home_team,
                        "leg_a_away_team": left_row.away_team,
                        "leg_a_home_team_zh": left_row.home_team_zh,
                        "leg_a_away_team_zh": left_row.away_team_zh,
                        "leg_a_scoreline": left_row.scoreline,
                        "leg_a_probability": float(left_row.model_probability),
                        "leg_a_decimal_odds": float(left_row.best_decimal_odds),
                        "leg_a_value_signal": left_row.value_signal,
                        "leg_b_match_no": int(right_row.match_no),
                        "leg_b_home_team": right_row.home_team,
                        "leg_b_away_team": right_row.away_team,
                        "leg_b_home_team_zh": right_row.home_team_zh,
                        "leg_b_away_team_zh": right_row.away_team_zh,
                        "leg_b_scoreline": right_row.scoreline,
                        "leg_b_probability": float(right_row.model_probability),
                        "leg_b_decimal_odds": float(right_row.best_decimal_odds),
                        "leg_b_value_signal": right_row.value_signal,
                        "joint_probability": joint_probability,
                        "joint_decimal_odds": joint_odds,
                        "return_per_2_stake": joint_odds * 2.0,
                        "expected_return_per_2_stake": joint_probability * joint_odds * 2.0,
                    }
                )
    return pd.DataFrame(rows)


def rank_high_hit_combos(
    combo_pool: pd.DataFrame,
    *,
    limit: int = 5,
) -> pd.DataFrame:
    if combo_pool.empty:
        return combo_pool.copy()
    return (
        combo_pool.sort_values(
            ["joint_probability", "expected_return_per_2_stake"],
            ascending=[False, False],
        )
        .head(limit)
        .reset_index(drop=True)
    )


def rank_high_payout_combos(
    combo_pool: pd.DataFrame,
    *,
    min_return_per_2_stake: float = 100.0,
    limit: int = 3,
) -> pd.DataFrame:
    if combo_pool.empty:
        return combo_pool.copy()
    filtered = combo_pool.loc[
        combo_pool["return_per_2_stake"].ge(min_return_per_2_stake)
    ].copy()
    return (
        filtered.sort_values(
            ["joint_probability", "expected_return_per_2_stake"],
            ascending=[False, False],
        )
        .head(limit)
        .reset_index(drop=True)
    )


def build_upset_scoreline_candidates(
    scoreline_analysis: pd.DataFrame,
    value_bets: pd.DataFrame,
    *,
    match_nos: list[int] | None = None,
) -> pd.DataFrame:
    if scoreline_analysis.empty:
        return pd.DataFrame()

    working = scoreline_analysis.copy()
    if match_nos is not None:
        working = working.loc[working["match_no"].isin(match_nos)].copy()
    summary = build_match_outcome_summary(working)
    if summary.empty:
        return pd.DataFrame()

    working["scoreline_outcome"] = working["scoreline"].map(scoreline_outcome_from_text)
    candidates = working.merge(
        summary[
            [
                "match_no",
                "favorite_outcome",
                "underdog_outcome",
                "favorite_probability",
                "underdog_probability",
                "upset_index",
            ]
        ],
        on="match_no",
        how="left",
    )
    candidates = candidates.loc[
        candidates["scoreline_outcome"].eq(candidates["underdog_outcome"])
    ].copy()

    odds_columns = [
        "match_no",
        "scoreline",
        "best_decimal_odds",
        "value_signal",
    ]
    if value_bets.empty:
        odds_frame = pd.DataFrame(columns=odds_columns)
    else:
        odds_frame = value_bets[odds_columns].drop_duplicates(
            subset=["match_no", "scoreline"]
        )
    candidates = candidates.merge(
        odds_frame,
        on=["match_no", "scoreline"],
        how="left",
    )
    return (
        candidates.sort_values(
            ["match_no", "scoreline_probability", "best_decimal_odds"],
            ascending=[True, False, False],
        )
        .groupby("match_no", sort=True)
        .head(1)
        .reset_index(drop=True)
    )


def rank_upset_combos(
    scoreline_analysis: pd.DataFrame,
    value_bets: pd.DataFrame,
    *,
    match_nos: list[int] | None = None,
    limit: int = 2,
) -> pd.DataFrame:
    candidates = build_upset_scoreline_candidates(
        scoreline_analysis,
        value_bets,
        match_nos=match_nos,
    )
    if candidates.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for left_row, right_row in combinations(candidates.itertuples(index=False), 2):
        left_odds = (
            float(left_row.best_decimal_odds)
            if pd.notna(left_row.best_decimal_odds)
            else np.nan
        )
        right_odds = (
            float(right_row.best_decimal_odds)
            if pd.notna(right_row.best_decimal_odds)
            else np.nan
        )
        joint_odds = (
            left_odds * right_odds
            if np.isfinite(left_odds) and np.isfinite(right_odds)
            else np.nan
        )
        rows.append(
            {
                "leg_a_match_no": int(left_row.match_no),
                "leg_a_home_team": left_row.home_team,
                "leg_a_away_team": left_row.away_team,
                "leg_a_home_team_zh": left_row.home_team_zh,
                "leg_a_away_team_zh": left_row.away_team_zh,
                "leg_a_scoreline": left_row.scoreline,
                "leg_a_probability": float(left_row.scoreline_probability),
                "leg_a_underdog_probability": float(left_row.underdog_probability),
                "leg_b_match_no": int(right_row.match_no),
                "leg_b_home_team": right_row.home_team,
                "leg_b_away_team": right_row.away_team,
                "leg_b_home_team_zh": right_row.home_team_zh,
                "leg_b_away_team_zh": right_row.away_team_zh,
                "leg_b_scoreline": right_row.scoreline,
                "leg_b_probability": float(right_row.scoreline_probability),
                "leg_b_underdog_probability": float(right_row.underdog_probability),
                "joint_probability": float(left_row.scoreline_probability)
                * float(right_row.scoreline_probability),
                "joint_upset_probability": float(left_row.underdog_probability)
                * float(right_row.underdog_probability),
                "joint_decimal_odds": joint_odds,
                "return_per_2_stake": joint_odds * 2.0 if np.isfinite(joint_odds) else np.nan,
            }
        )
    combo_frame = pd.DataFrame(rows)
    if combo_frame.empty:
        return combo_frame
    return (
        combo_frame.sort_values(
            ["joint_upset_probability", "joint_probability"],
            ascending=[False, False],
        )
        .head(limit)
        .reset_index(drop=True)
    )
