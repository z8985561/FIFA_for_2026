from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error, mean_poisson_deviance
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .baseline_model import chronological_split
from .data_pipeline import prepare_research_data
from .enhanced_features import (
    build_2026_enhanced_features,
    build_historical_enhanced_features,
    enhanced_feature_columns,
)
from .feature_store import prepare_match_feature_store
from .lineups_pipeline import TEAM_NAME_ZH, prepare_predicted_lineups
from .project_paths import (
    MATCH_FEATURE_STORE_2026_PATH,
    MATCHES_PATH,
    PREDICTED_LINEUPS_PATH,
    SCORELINE_ANALYSIS_PATH,
    SCORELINE_METRICS_PATH,
    ensure_project_directories,
)

DEFAULT_MAX_GOALS = 7
DEFAULT_TOP_SCORES = 10
MAX_LINEUP_LOG_ADJUSTMENT = 0.12

PLAYER_ATTACK_IMPACTS = {
    "Christian Pulisic": 0.05,
    "Son Heung-min": 0.055,
    "Patrik Schick": 0.05,
    "Julio Enciso": 0.04,
    "Hwang Hee-chan": 0.035,
    "Folarin Balogun": 0.035,
    "Miguel Almiron": 0.035,
    "Jonathan David": 0.04,
    "Cyle Larin": 0.025,
    "Raul Jimenez": 0.03,
    "Julian Quinones": 0.025,
    "Lyle Foster": 0.025,
    "Antonio Sanabria": 0.025,
    "Lee Jae-sung": 0.018,
    "Malik Tillman": 0.02,
    "Pavel Sulc": 0.018,
    "Lukas Provod": 0.018,
}

PLAYER_DEFENSE_IMPACTS = {
    "Kim Min-jae": 0.045,
    "Gustavo Gomez": 0.04,
    "Tyler Adams": 0.03,
    "Tomas Soucek": 0.025,
    "Edson Alvarez": 0.03,
    "Ronwen Williams": 0.02,
    "Guillermo Ochoa": 0.018,
    "Alistair Johnston": 0.018,
    "Stephen Eustaquio": 0.018,
    "Chris Richards": 0.018,
    "Omar Alderete": 0.018,
    "Junior Alonso": 0.018,
}

FORMATION_ATTACK_IMPACTS = {
    "3-4-3": 0.018,
    "4-3-3": 0.014,
    "3-4-2-1": 0.01,
    "4-2-3-1": 0.004,
}

FORMATION_DEFENSE_IMPACTS = {
    "4-2-3-1": 0.01,
    "3-4-2-1": 0.006,
    "4-3-3": 0.0,
    "3-4-3": -0.004,
}


@dataclass(frozen=True)
class ScorelineMetrics:
    train_matches: int
    test_matches: int
    feature_count: int
    dixon_coles_rho: float
    home_goal_mae: float
    away_goal_mae: float
    home_poisson_deviance: float
    away_poisson_deviance: float


@dataclass(frozen=True)
class ScorelineOutputs:
    metrics_path: str
    analysis_path: str
    metrics: ScorelineMetrics
    matches_analyzed: int
    rows: int


def ensure_scoreline_inputs() -> None:
    if not MATCHES_PATH.exists():
        prepare_research_data()
    if not MATCH_FEATURE_STORE_2026_PATH.exists():
        prepare_match_feature_store()
    if not PREDICTED_LINEUPS_PATH.exists():
        prepare_predicted_lineups()


def train_scoreline_models(
    historical_features: pd.DataFrame,
) -> tuple[object, object, ScorelineMetrics]:
    train_frame, test_frame = chronological_split(historical_features)
    columns = enhanced_feature_columns()

    home_model = make_pipeline(
        StandardScaler(),
        PoissonRegressor(alpha=0.01, max_iter=1000),
    )
    away_model = make_pipeline(
        StandardScaler(),
        PoissonRegressor(alpha=0.01, max_iter=1000),
    )

    home_model.fit(train_frame[columns], train_frame["home_score"])
    away_model.fit(train_frame[columns], train_frame["away_score"])

    train_home_rates = clip_goal_rates(home_model.predict(train_frame[columns]))
    train_away_rates = clip_goal_rates(away_model.predict(train_frame[columns]))
    dixon_coles_rho = estimate_dixon_coles_rho(
        train_frame["home_score"].to_numpy(),
        train_frame["away_score"].to_numpy(),
        train_home_rates,
        train_away_rates,
    )

    home_predictions = clip_goal_rates(home_model.predict(test_frame[columns]))
    away_predictions = clip_goal_rates(away_model.predict(test_frame[columns]))
    metrics = ScorelineMetrics(
        train_matches=len(train_frame),
        test_matches=len(test_frame),
        feature_count=len(columns),
        dixon_coles_rho=dixon_coles_rho,
        home_goal_mae=float(mean_absolute_error(test_frame["home_score"], home_predictions)),
        away_goal_mae=float(mean_absolute_error(test_frame["away_score"], away_predictions)),
        home_poisson_deviance=float(
            mean_poisson_deviance(test_frame["home_score"], home_predictions)
        ),
        away_poisson_deviance=float(
            mean_poisson_deviance(test_frame["away_score"], away_predictions)
        ),
    )
    return home_model, away_model, metrics


def clip_goal_rates(values: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), 0.05, 6.0)


def clamp_lineup_adjustment(value: float) -> float:
    return float(np.clip(value, -MAX_LINEUP_LOG_ADJUSTMENT, MAX_LINEUP_LOG_ADJUSTMENT))


def lineup_adjustment_summary(predicted_lineups: pd.DataFrame) -> pd.DataFrame:
    if predicted_lineups.empty:
        return pd.DataFrame(
            columns=[
                "match_no",
                "team_name",
                "lineup_attack_impact",
                "lineup_defense_impact",
                "lineup_status",
                "formation",
            ]
        )

    rows: list[dict[str, object]] = []
    for (match_no, team_name), group in predicted_lineups.groupby(
        ["match_no", "team_name"],
        sort=True,
    ):
        formation = str(group["formation"].iloc[0])
        attack_impact = FORMATION_ATTACK_IMPACTS.get(formation, 0.0) + float(
            group["player_name"].map(PLAYER_ATTACK_IMPACTS).fillna(0.0).sum()
        )
        defense_impact = FORMATION_DEFENSE_IMPACTS.get(formation, 0.0) + float(
            group["player_name"].map(PLAYER_DEFENSE_IMPACTS).fillna(0.0).sum()
        )
        rows.append(
            {
                "match_no": int(match_no),
                "team_name": str(team_name),
                "lineup_attack_impact": attack_impact,
                "lineup_defense_impact": defense_impact,
                "lineup_status": str(group["lineup_status"].iloc[0]),
                "formation": formation,
            }
        )
    return pd.DataFrame(rows)


def lineup_adjustment_for_team(
    lineup_summary: pd.DataFrame,
    *,
    match_no: int,
    team_name: str,
) -> dict[str, object]:
    if lineup_summary.empty:
        return {
            "lineup_attack_impact": 0.0,
            "lineup_defense_impact": 0.0,
            "lineup_status": None,
            "formation": None,
        }
    rows = lineup_summary.loc[
        lineup_summary["match_no"].eq(match_no) & lineup_summary["team_name"].eq(team_name)
    ]
    if rows.empty:
        return {
            "lineup_attack_impact": 0.0,
            "lineup_defense_impact": 0.0,
            "lineup_status": None,
            "formation": None,
        }
    return rows.iloc[0].to_dict()


def apply_lineup_goal_rate_adjustment(
    *,
    home_goal_rate: float,
    away_goal_rate: float,
    home_lineup: dict[str, object],
    away_lineup: dict[str, object],
) -> dict[str, float]:
    home_log_adjustment = clamp_lineup_adjustment(
        float(home_lineup["lineup_attack_impact"])
        - float(away_lineup["lineup_defense_impact"])
    )
    away_log_adjustment = clamp_lineup_adjustment(
        float(away_lineup["lineup_attack_impact"])
        - float(home_lineup["lineup_defense_impact"])
    )
    home_factor = math.exp(home_log_adjustment)
    away_factor = math.exp(away_log_adjustment)
    adjusted_rates = clip_goal_rates(
        np.array([home_goal_rate * home_factor, away_goal_rate * away_factor])
    )
    return {
        "home_lineup_log_adjustment": home_log_adjustment,
        "away_lineup_log_adjustment": away_log_adjustment,
        "home_lineup_goal_factor": float(home_factor),
        "away_lineup_goal_factor": float(away_factor),
        "home_expected_goals": float(adjusted_rates[0]),
        "away_expected_goals": float(adjusted_rates[1]),
    }


def poisson_probability(goals: int, rate: float) -> float:
    return math.exp(-rate) * (rate**goals) / math.factorial(goals)


def dixon_coles_factor(
    home_goals: int,
    away_goals: int,
    home_goal_rate: float,
    away_goal_rate: float,
    rho: float,
) -> float:
    if home_goals == 0 and away_goals == 0:
        return max(1.0 - home_goal_rate * away_goal_rate * rho, 1e-9)
    if home_goals == 0 and away_goals == 1:
        return max(1.0 + home_goal_rate * rho, 1e-9)
    if home_goals == 1 and away_goals == 0:
        return max(1.0 + away_goal_rate * rho, 1e-9)
    if home_goals == 1 and away_goals == 1:
        return max(1.0 - rho, 1e-9)
    return 1.0


def estimate_dixon_coles_rho(
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    home_goal_rates: np.ndarray,
    away_goal_rates: np.ndarray,
) -> float:
    candidate_rhos = np.linspace(-0.08, 0.08, 65)
    best_rho = 0.0
    best_loss = float("inf")

    for rho in candidate_rhos:
        loss = 0.0
        for actual_home, actual_away, home_rate, away_rate in zip(
            home_goals,
            away_goals,
            home_goal_rates,
            away_goal_rates,
            strict=True,
        ):
            probability = (
                poisson_probability(int(actual_home), float(home_rate))
                * poisson_probability(int(actual_away), float(away_rate))
                * dixon_coles_factor(
                    int(actual_home),
                    int(actual_away),
                    float(home_rate),
                    float(away_rate),
                    float(rho),
                )
            )
            loss -= math.log(max(probability, 1e-12))
        if loss < best_loss:
            best_loss = loss
            best_rho = float(rho)
    return best_rho


def scoreline_matrix(
    home_goal_rate: float,
    away_goal_rate: float,
    *,
    max_goals: int = DEFAULT_MAX_GOALS,
    rho: float = 0.0,
) -> pd.DataFrame:
    rows = []
    for home_goals in range(max_goals + 1):
        home_probability = poisson_probability(home_goals, home_goal_rate)
        for away_goals in range(max_goals + 1):
            adjustment = dixon_coles_factor(
                home_goals,
                away_goals,
                home_goal_rate,
                away_goal_rate,
                rho,
            )
            rows.append(
                {
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "scoreline": f"{home_goals}-{away_goals}",
                    "probability": home_probability
                    * poisson_probability(away_goals, away_goal_rate)
                    * adjustment,
                }
            )

    matrix = pd.DataFrame(rows)
    matrix["probability"] = matrix["probability"] / matrix["probability"].sum()
    return matrix


def matrix_summary(matrix: pd.DataFrame) -> dict[str, float]:
    home_win_probability = matrix.loc[
        matrix["home_goals"] > matrix["away_goals"],
        "probability",
    ].sum()
    draw_probability = matrix.loc[
        matrix["home_goals"] == matrix["away_goals"],
        "probability",
    ].sum()
    away_win_probability = matrix.loc[
        matrix["home_goals"] < matrix["away_goals"],
        "probability",
    ].sum()
    over_2_5_probability = matrix.loc[
        matrix["home_goals"] + matrix["away_goals"] >= 3,
        "probability",
    ].sum()
    both_teams_score_probability = matrix.loc[
        (matrix["home_goals"] > 0) & (matrix["away_goals"] > 0),
        "probability",
    ].sum()
    return {
        "score_home_win_probability": float(home_win_probability),
        "score_draw_probability": float(draw_probability),
        "score_away_win_probability": float(away_win_probability),
        "over_2_5_probability": float(over_2_5_probability),
        "under_2_5_probability": float(1.0 - over_2_5_probability),
        "both_teams_score_probability": float(both_teams_score_probability),
        "clean_sheet_home_probability": float(
            matrix.loc[matrix["away_goals"] == 0, "probability"].sum()
        ),
        "clean_sheet_away_probability": float(
            matrix.loc[matrix["home_goals"] == 0, "probability"].sum()
        ),
    }


def inflate_scoreline_probability(
    matrix: pd.DataFrame,
    *,
    scoreline: str,
    multiplier: float,
) -> pd.DataFrame:
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    adjusted = matrix.copy()
    adjusted.loc[adjusted["scoreline"].eq(scoreline), "probability"] *= multiplier
    adjusted["probability"] = adjusted["probability"] / adjusted["probability"].sum()
    return adjusted


def build_scoreline_analysis(
    fixture_features: pd.DataFrame,
    home_model: object,
    away_model: object,
    *,
    rho: float,
    limit: int,
    max_goals: int,
    top_scores: int,
    predicted_lineups: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = enhanced_feature_columns()
    fixtures = fixture_features.sort_values(["date_et", "match_no"]).head(limit).copy()
    home_rates = clip_goal_rates(home_model.predict(fixtures[columns]))
    away_rates = clip_goal_rates(away_model.predict(fixtures[columns]))
    lineup_summary = lineup_adjustment_summary(
        pd.DataFrame() if predicted_lineups is None else predicted_lineups
    )

    rows = []
    for row, home_rate, away_rate in zip(
        fixtures.itertuples(index=False),
        home_rates,
        away_rates,
        strict=True,
    ):
        home_lineup = lineup_adjustment_for_team(
            lineup_summary,
            match_no=int(row.match_no),
            team_name=str(row.home_team),
        )
        away_lineup = lineup_adjustment_for_team(
            lineup_summary,
            match_no=int(row.match_no),
            team_name=str(row.away_team),
        )
        lineup_adjustment = apply_lineup_goal_rate_adjustment(
            home_goal_rate=float(home_rate),
            away_goal_rate=float(away_rate),
            home_lineup=home_lineup,
            away_lineup=away_lineup,
        )
        matrix = scoreline_matrix(
            float(lineup_adjustment["home_expected_goals"]),
            float(lineup_adjustment["away_expected_goals"]),
            max_goals=max_goals,
            rho=rho,
        )
        summary = matrix_summary(matrix)
        top_matrix = matrix.sort_values("probability", ascending=False).head(top_scores)
        for rank, score_row in enumerate(top_matrix.itertuples(index=False), start=1):
            rows.append(
                {
                    "match_no": row.match_no,
                    "stage": row.stage,
                    "group_name": row.group_name,
                    "date_et": row.date_et,
                    "home_team": row.home_team,
                    "away_team": row.away_team,
                    "home_team_zh": TEAM_NAME_ZH.get(str(row.home_team), str(row.home_team)),
                    "away_team_zh": TEAM_NAME_ZH.get(str(row.away_team), str(row.away_team)),
                    "raw_home_expected_goals": float(home_rate),
                    "raw_away_expected_goals": float(away_rate),
                    "home_expected_goals": float(lineup_adjustment["home_expected_goals"]),
                    "away_expected_goals": float(lineup_adjustment["away_expected_goals"]),
                    "home_lineup_goal_factor": lineup_adjustment["home_lineup_goal_factor"],
                    "away_lineup_goal_factor": lineup_adjustment["away_lineup_goal_factor"],
                    "home_lineup_log_adjustment": lineup_adjustment[
                        "home_lineup_log_adjustment"
                    ],
                    "away_lineup_log_adjustment": lineup_adjustment[
                        "away_lineup_log_adjustment"
                    ],
                    "home_lineup_status": home_lineup["lineup_status"],
                    "away_lineup_status": away_lineup["lineup_status"],
                    "home_formation": home_lineup["formation"],
                    "away_formation": away_lineup["formation"],
                    "dixon_coles_rho": rho,
                    **summary,
                    "scoreline_rank": rank,
                    "scoreline": score_row.scoreline,
                    "scoreline_probability": float(score_row.probability),
                }
            )
    return pd.DataFrame(rows)


def prepare_scoreline_analysis(
    *,
    limit: int = 4,
    max_goals: int = DEFAULT_MAX_GOALS,
    top_scores: int = DEFAULT_TOP_SCORES,
    output_path: str | None = None,
) -> ScorelineOutputs:
    ensure_project_directories()
    ensure_scoreline_inputs()

    matches = pd.read_parquet(MATCHES_PATH)
    match_features = pd.read_parquet(MATCH_FEATURE_STORE_2026_PATH)
    predicted_lineups = pd.read_parquet(PREDICTED_LINEUPS_PATH)
    historical_features = build_historical_enhanced_features(matches)
    fixture_features = build_2026_enhanced_features(match_features, matches)

    home_model, away_model, metrics = train_scoreline_models(historical_features)
    analysis = build_scoreline_analysis(
        fixture_features,
        home_model,
        away_model,
        rho=metrics.dixon_coles_rho,
        limit=limit,
        max_goals=max_goals,
        top_scores=top_scores,
        predicted_lineups=predicted_lineups,
    )

    SCORELINE_METRICS_PATH.write_text(
        json.dumps(asdict(metrics), indent=2),
        encoding="utf-8",
    )
    path = (
        SCORELINE_ANALYSIS_PATH
        if output_path is None
        else SCORELINE_ANALYSIS_PATH.parent / output_path
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    analysis.to_csv(path, index=False, encoding="utf-8-sig")
    return ScorelineOutputs(
        metrics_path=str(SCORELINE_METRICS_PATH),
        analysis_path=str(path),
        metrics=metrics,
        matches_analyzed=limit,
        rows=len(analysis),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate scoreline probabilities for fixtures.")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--max-goals", type=int, default=DEFAULT_MAX_GOALS)
    parser.add_argument("--top-scores", type=int, default=DEFAULT_TOP_SCORES)
    parser.add_argument("--output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_scoreline_analysis(
        limit=args.limit,
        max_goals=args.max_goals,
        top_scores=args.top_scores,
        output_path=args.output,
    )
    print(f"metrics_path: {outputs.metrics_path}")
    print(f"analysis_path: {outputs.analysis_path}")
    print(json.dumps(asdict(outputs.metrics), indent=2))
    print(f"matches_analyzed: {outputs.matches_analyzed}")
    print(f"rows: {outputs.rows}")


if __name__ == "__main__":
    main()
