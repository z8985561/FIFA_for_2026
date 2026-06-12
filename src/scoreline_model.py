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
    SPORTTERY_MARKET_ODDS_SNAPSHOTS_PATH,
    ensure_project_directories,
)

DEFAULT_MAX_GOALS = 7
DEFAULT_TOP_SCORES = 10
MAX_LINEUP_LOG_ADJUSTMENT = 0.12
DEFAULT_MARKET_OUTCOME_ANCHOR_WEIGHT = 0.25
DEFAULT_MARKET_TOTAL_GOALS_ANCHOR_WEIGHT = 0.35
GROUP_OPENER_MISMATCH_ELO_THRESHOLD = 150.0
GROUP_OPENER_FAVORITE_ATTACK_LOG_BOOST = 0.045

PLAYER_ATTACK_IMPACTS = {
    # Group A
    "Raul Jimenez": 0.03,
    "Julian Quinones": 0.025,
    "Roberto Alvarado": 0.02,
    "Lyle Foster": 0.025,
    "Relebohile Mofokeng": 0.018,
    "Son Heung-min": 0.055,
    "Hwang Hee-chan": 0.035,
    "Lee Jae-sung": 0.018,
    "Patrik Schick": 0.05,
    "Pavel Sulc": 0.018,
    "Lukas Provod": 0.018,
    # Group B
    "Jonathan David": 0.04,
    "Cyle Larin": 0.025,
    "Tajon Buchanan": 0.02,
    "Ermedin Demirovic": 0.04,
    "Sehic": 0.0,
    "Akram Afif": 0.04,
    "Almoez Ali": 0.025,
    "Breel Embolo": 0.035,
    "Ruben Vargas": 0.025,
    "Dan Ndoye": 0.022,
    # Group C
    "Vinicius Jr": 0.06,
    "Raphinha": 0.045,
    "Rodrygo": 0.04,
    "Cunha": 0.03,
    "Paqueta": 0.025,
    "Hakimi": 0.025,
    "Ziyech": 0.03,
    "En-Nesyri": 0.035,
    "El Khannouss": 0.022,
    "Oswald Thill": 0.018,
    "Frantzdy Pierrot": 0.022,
    "Lawrence Shankland": 0.025,
    "Che Adams": 0.022,
    "Scott McTominay": 0.025,
    # Group D
    "Christian Pulisic": 0.05,
    "Folarin Balogun": 0.035,
    "Malik Tillman": 0.02,
    "Ricardo Pepi": 0.025,
    "Julio Enciso": 0.04,
    "Miguel Almiron": 0.035,
    "Antonio Sanabria": 0.025,
    "Adam Taggart": 0.022,
    "Mitchell Duke": 0.018,
    "Kerem Akturkoglu": 0.03,
    "Yusuf Yazici": 0.025,
    "Arda Guler": 0.04,
    "Kenan Yildiz": 0.035,
    # Group E
    "Jamal Musiala": 0.055,
    "Florian Wirtz": 0.055,
    "Leroy Sane": 0.04,
    "Kai Havertz": 0.035,
    "Thomas Muller": 0.025,
    "Sebastien Haller": 0.03,
    "Nicolas Pepe": 0.025,
    "Franck Kessie": 0.025,
    "Enner Valencia": 0.04,
    "Jeremy Sarmiento": 0.025,
    "Moisés Caicedo": 0.025,
    # Group F
    "Cody Gakpo": 0.04,
    "Memphis Depay": 0.04,
    "Donyell Malen": 0.03,
    "Xavi Simons": 0.03,
    "Wout Weghorst": 0.025,
    "Ayase Ueda": 0.035,
    "Takefusa Kubo": 0.04,
    "Junya Ito": 0.03,
    "Kaoru Mitoma": 0.04,
    "Wahbi Khazri": 0.025,
    "Taha Yassine Khenissi": 0.022,
    "Hannibal Mejbri": 0.025,
    "Viktor Gyokeres": 0.055,
    "Alexander Isak": 0.05,
    "Dejan Kulusevski": 0.035,
    # Group G
    "Romelu Lukaku": 0.045,
    "Lois Openda": 0.04,
    "Kevin De Bruyne": 0.045,
    "Leandro Trossard": 0.025,
    "Mohamed Salah": 0.06,
    "Omar Marmoush": 0.04,
    "Mostafa Mohamed": 0.025,
    "Sardar Azmoun": 0.035,
    "Mehdi Taremi": 0.04,
    "Saman Ghoddos": 0.022,
    "Chris Wood": 0.035,
    "Marko Stamenic": 0.022,
    # Group H
    "Alvaro Morata": 0.035,
    "Ferran Torres": 0.03,
    "Pedri": 0.025,
    "Yamal Lamine": 0.04,
    "Darwin Nunez": 0.045,
    "Luis Suarez": 0.025,
    "Rodrigo Bentancur": 0.02,
    "Fakhreddine Ben Youssef": 0.022,
    "Ferjani Sassi": 0.018,
    # Group I
    "Kylian Mbappe": 0.065,
    "Antoine Griezmann": 0.04,
    "Ousmane Dembele": 0.04,
    "Marcus Thuram": 0.035,
    "Sadio Mane": 0.045,
    "Ismaila Sarr": 0.035,
    "Iliman Ndiaye": 0.03,
    "Erling Haaland": 0.065,
    "Martin Odegaard": 0.04,
    "Alexander Sorloth": 0.035,
    "Aiymen Asad": 0.022,
    "Aymen Hussein": 0.025,
    # Group J
    "Lionel Messi": 0.07,
    "Julian Alvarez": 0.05,
    "Lautaro Martinez": 0.05,
    "Angel Di Maria": 0.03,
    "Islam Slimani": 0.025,
    "Riyad Mahrez": 0.04,
    "Youcef Atal": 0.025,
    "Marko Arnautovic": 0.035,
    "Marcel Sabitzer": 0.025,
    "Michael Gregoritsch": 0.022,
    "Yazan Al Naimat": 0.025,
    "Musa Al Taamari": 0.025,
    # Group K
    "Cristiano Ronaldo": 0.055,
    "Bruno Fernandes": 0.045,
    "Rafael Leao": 0.04,
    "Pedro Neto": 0.03,
    "Bernardo Silva": 0.035,
    "Cédric Bakambu": 0.03,
    "Yoane Wissa": 0.03,
    "Sirojiddin Jaloliddinov": 0.022,
    "Abbosbek Fayzullaev": 0.025,
    "Luis Diaz": 0.045,
    "James Rodriguez": 0.04,
    "Jhon Duran": 0.035,
    "Rafael Santos Borre": 0.025,
    # Group L
    "Harry Kane": 0.06,
    "Phil Foden": 0.045,
    "Bukayo Saka": 0.045,
    "Jude Bellingham": 0.05,
    "Marcus Rashford": 0.03,
    "Luka Modric": 0.035,
    "Andrej Kramaric": 0.035,
    "Ivan Perisic": 0.025,
    "Jordan Ayew": 0.025,
    "Antoine Semenyo": 0.025,
    "Mohammed Kudus": 0.04,
    "Jose Fajardo": 0.022,
    "Ismael Tejada": 0.018,
}

PLAYER_DEFENSE_IMPACTS = {
    # Group A
    "Guillermo Ochoa": 0.018,
    "Edson Alvarez": 0.03,
    "Cesar Montes": 0.018,
    "Ronwen Williams": 0.02,
    "Siyanda Xulu": 0.015,
    "Kim Min-jae": 0.045,
    "Lee Gi-hyuk": 0.018,
    "Tomas Soucek": 0.025,
    "Robin Hranac": 0.02,
    # Group B
    "Alistair Johnston": 0.018,
    "Derek Cornelius": 0.018,
    "Stephen Eustaquio": 0.018,
    "Maxime Crepeau": 0.018,
    "Nikola Vasilj": 0.02,
    "Yann Sommer": 0.03,
    "Manuel Akanji": 0.03,
    "Granit Xhaka": 0.025,
    # Group C
    "Alisson": 0.035,
    "Marquinhos": 0.035,
    "Gabriel Magalhaes": 0.03,
    "Casemiro": 0.028,
    "Yassine Bounou": 0.03,
    "Romain Saiss": 0.025,
    "Achraf Dari": 0.022,
    "Sofyan Amrabat": 0.03,
    "Loic Badiashile": 0.018,
    "Lyle Taylor": 0.015,
    "Grant Hanley": 0.022,
    "Andrew Robertson": 0.025,
    # Group D
    "Tyler Adams": 0.03,
    "Chris Richards": 0.018,
    "Matt Freese": 0.02,
    "Gustavo Gomez": 0.04,
    "Omar Alderete": 0.018,
    "Junior Alonso": 0.018,
    "Mat Ryan": 0.025,
    "Harry Souttar": 0.022,
    "Mert Muldur": 0.018,
    "Merih Demiral": 0.03,
    "Abdülkerim Bardakci": 0.022,
    "Cagatay Cakir": 0.018,
    # Group E
    "Manuel Neuer": 0.025,
    "Joshua Kimmich": 0.03,
    "Jonathan Tah": 0.025,
    "Nico Schlotterbeck": 0.022,
    "Serge Gnabry": 0.018,
    "Geronimo Rulli": 0.018,
    "Simon Adingra": 0.015,
    "Willian Pacho": 0.025,
    "Byron Castillo": 0.018,
    # Group F
    "Virgil van Dijk": 0.04,
    "Nathan Ake": 0.025,
    "Bart Verbruggen": 0.022,
    "Micky van de Ven": 0.025,
    "Wataru Endo": 0.025,
    "Itakura Ko": 0.025,
    "Moez Hassan": 0.018,
    "Montassar Talbi": 0.02,
    "Victor Lindelof": 0.025,
    "Isak Hien": 0.025,
    "Marcus Danielson": 0.018,
    # Group G
    "Wout Faes": 0.022,
    "Jan Vertonghen": 0.022,
    "Koen Casteels": 0.025,
    "Ahmed El Shenawy": 0.022,
    "Omar Kamal": 0.018,
    "Alireza Beiranvand": 0.025,
    "Shoja Khalilzadeh": 0.022,
    "Ehsan Hajsafi": 0.02,
    "Joe Bell": 0.018,
    "Winston Reid": 0.018,
    # Group H
    "Unai Simon": 0.025,
    "Aymeric Laporte": 0.03,
    "Robin Le Normand": 0.025,
    "Jose Maria Gimenez": 0.03,
    "Ronald Araujo": 0.03,
    "Sebastian Coates": 0.022,
    "Sergio Rochet": 0.022,
    # Group I
    "Mike Maignan": 0.03,
    "William Saliba": 0.035,
    "Dayot Upamecano": 0.03,
    "N'Golo Kante": 0.03,
    "Kalidou Koulibaly": 0.03,
    "Formose Mendy": 0.022,
    "Alexander Sorloth": 0.0,
    "Erling Haaland": 0.0,
    "Ola Aina": 0.018,
    "Andreas Hanche-Olsen": 0.022,
    "Orjan Nyland": 0.022,
    "Ahmed Ibrahim": 0.018,
    # Group J
    "Cristian Romero": 0.035,
    "Nicolas Otamendi": 0.025,
    "Lisandro Martinez": 0.035,
    "Emiliano Martinez": 0.035,
    "Djamel Benlamri": 0.018,
    "Rayan Ait Nouri": 0.02,
    "David Alaba": 0.03,
    "Philipp Lienhart": 0.022,
    "Patrick Pentz": 0.018,
    "Yasser Abuhelyeh": 0.02,
    "Musa Al Taamari": 0.0,
    # Group K
    "Diogo Costa": 0.028,
    "Ruben Dias": 0.04,
    "Pepe": 0.022,
    "Joao Cancelo": 0.025,
    "Chancel Mbemba": 0.022,
    "Sirojiddin Jaloliddinov": 0.0,
    "Rustam Yusupov": 0.018,
    "Davinson Sanchez": 0.028,
    "Daniel Munoz": 0.02,
    "Carlos Cuesta": 0.022,
    # Group L
    "Jordan Pickford": 0.025,
    "John Stones": 0.03,
    "Kyle Walker": 0.025,
    "Marc Guehi": 0.025,
    "Declan Rice": 0.035,
    "Dominik Livakovic": 0.03,
    "Josko Gvardiol": 0.035,
    "Dejan Lovren": 0.022,
    "Lawrence Ati-Zigi": 0.022,
    "Daniel Amartey": 0.022,
    "Jose Fajardo": 0.0,
    "Freddy Gondola": 0.018,
}

FORMATION_ATTACK_IMPACTS = {
    "3-4-3": 0.018,
    "4-3-3": 0.014,
    "3-4-2-1": 0.01,
    "4-2-3-1": 0.004,
    "4-4-2": 0.008,
    "3-5-2": 0.006,
    "5-3-2": 0.002,
    "4-1-4-1": 0.004,
    "3-4-1-2": 0.01,
    "5-4-1": -0.002,
    "4-5-1": -0.004,
    "5-2-3": 0.008,
}

FORMATION_DEFENSE_IMPACTS = {
    "4-2-3-1": 0.01,
    "3-4-2-1": 0.006,
    "4-3-3": 0.0,
    "3-4-3": -0.004,
    "4-4-2": 0.008,
    "3-5-2": 0.01,
    "5-3-2": 0.014,
    "4-1-4-1": 0.012,
    "3-4-1-2": 0.008,
    "5-4-1": 0.016,
    "4-5-1": 0.014,
    "5-2-3": 0.008,
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


def add_group_match_rounds(fixtures: pd.DataFrame) -> pd.DataFrame:
    if fixtures.empty or "group_name" not in fixtures.columns:
        return fixtures.copy()
    enriched = fixtures.copy()
    enriched["group_match_order"] = (
        enriched.sort_values(["date_et", "match_no"])
        .groupby("group_name", dropna=False)
        .cumcount()
        + 1
    )
    enriched["group_match_round"] = ((enriched["group_match_order"] - 1) // 2 + 1).astype(int)
    return enriched.drop(columns=["group_match_order"])


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


def apply_group_opener_mismatch_adjustment(
    *,
    home_goal_rate: float,
    away_goal_rate: float,
    stage: object,
    group_match_round: object,
    elo_diff: object,
    home_team: str,
    away_team: str,
    elo_threshold: float = GROUP_OPENER_MISMATCH_ELO_THRESHOLD,
    favorite_attack_log_boost: float = GROUP_OPENER_FAVORITE_ATTACK_LOG_BOOST,
) -> dict[str, object]:
    try:
        round_number = int(group_match_round)
        elo_difference = float(elo_diff)
    except (TypeError, ValueError):
        round_number = 0
        elo_difference = 0.0

    favorite_elo_edge = abs(elo_difference)
    is_group_opener = str(stage) == "Group Stage" and round_number == 1
    applied = is_group_opener and favorite_elo_edge >= elo_threshold
    home_log_adjustment = 0.0
    away_log_adjustment = 0.0
    favorite_team = None

    if applied:
        if elo_difference >= 0:
            home_log_adjustment = favorite_attack_log_boost
            favorite_team = home_team
        else:
            away_log_adjustment = favorite_attack_log_boost
            favorite_team = away_team

    adjusted_rates = clip_goal_rates(
        np.array(
            [
                home_goal_rate * math.exp(home_log_adjustment),
                away_goal_rate * math.exp(away_log_adjustment),
            ]
        )
    )
    return {
        "group_opener_mismatch_adjustment_applied": bool(applied),
        "group_opener_favorite_team": favorite_team,
        "group_opener_favorite_elo_edge": float(favorite_elo_edge),
        "home_group_opener_log_adjustment": float(home_log_adjustment),
        "away_group_opener_log_adjustment": float(away_log_adjustment),
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


def scoreline_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home_win"
    if home_goals < away_goals:
        return "away_win"
    return "draw"


def total_goals_bucket(home_goals: int, away_goals: int) -> str:
    total_goals = int(home_goals) + int(away_goals)
    return "total_goals_7_plus" if total_goals >= 7 else f"total_goals_{total_goals}"


def fair_probabilities_from_decimal_odds(
    rows: pd.DataFrame,
    *,
    outcome_column: str,
) -> dict[str, float]:
    if rows.empty:
        return {}
    working = rows.copy()
    working["decimal_odds"] = pd.to_numeric(working["decimal_odds"], errors="coerce")
    working = working.loc[working["decimal_odds"].gt(1.0)].copy()
    if working.empty:
        return {}
    working["raw_probability"] = 1.0 / working["decimal_odds"]
    probability_sum = float(working["raw_probability"].sum())
    if probability_sum <= 0:
        return {}
    return {
        str(row[outcome_column]): float(row["raw_probability"] / probability_sum)
        for _, row in working.iterrows()
    }


def build_scoreline_market_constraints(
    sporttery_market_odds_snapshots: pd.DataFrame,
) -> pd.DataFrame:
    if sporttery_market_odds_snapshots.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for match_no, group in sporttery_market_odds_snapshots.groupby("match_no", sort=True):
        had_probabilities = fair_probabilities_from_decimal_odds(
            group.loc[group["market_code"].eq("HAD")],
            outcome_column="outcome_code",
        )
        ttg_probabilities = fair_probabilities_from_decimal_odds(
            group.loc[group["market_code"].eq("TTG")],
            outcome_column="outcome_code",
        )
        rows.append(
            {
                "match_no": int(match_no),
                "has_market_outcome_constraint": {
                    "home_win",
                    "draw",
                    "away_win",
                }.issubset(had_probabilities),
                "market_home_win_probability": had_probabilities.get("home_win"),
                "market_draw_probability": had_probabilities.get("draw"),
                "market_away_win_probability": had_probabilities.get("away_win"),
                "has_market_total_goals_constraint": bool(ttg_probabilities),
                "market_total_goals_probabilities": ttg_probabilities,
            }
        )
    return pd.DataFrame(rows)


def constraint_for_match(
    market_constraints: pd.DataFrame,
    *,
    match_no: int,
) -> dict[str, object]:
    if market_constraints.empty:
        return {}
    rows = market_constraints.loc[market_constraints["match_no"].eq(match_no)]
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


def apply_market_probability_anchor(
    matrix: pd.DataFrame,
    *,
    category_column: str,
    target_probabilities: dict[str, float],
    weight: float,
) -> pd.DataFrame:
    if not target_probabilities or weight <= 0:
        return matrix
    if weight > 1:
        raise ValueError("weight must be less than or equal to 1")

    adjusted = matrix.copy()
    model_probabilities = adjusted.groupby(category_column)["probability"].sum().to_dict()
    multipliers = {}
    for category, target_probability in target_probabilities.items():
        model_probability = float(model_probabilities.get(category, 0.0))
        if model_probability <= 0 or target_probability is None:
            continue
        target_ratio = float(target_probability) / model_probability
        multipliers[category] = (1.0 - weight) + weight * target_ratio

    if not multipliers:
        return matrix
    adjusted["probability"] = adjusted["probability"] * adjusted[category_column].map(
        multipliers
    ).fillna(1.0)
    adjusted["probability"] = adjusted["probability"] / adjusted["probability"].sum()
    return adjusted


def apply_market_scoreline_constraints(
    matrix: pd.DataFrame,
    constraint: dict[str, object],
    *,
    outcome_weight: float = DEFAULT_MARKET_OUTCOME_ANCHOR_WEIGHT,
    total_goals_weight: float = DEFAULT_MARKET_TOTAL_GOALS_ANCHOR_WEIGHT,
) -> pd.DataFrame:
    if not constraint:
        return matrix

    adjusted = matrix.copy()
    adjusted["outcome_bucket"] = [
        scoreline_outcome(int(row.home_goals), int(row.away_goals))
        for row in adjusted.itertuples(index=False)
    ]
    adjusted["total_goals_bucket"] = [
        total_goals_bucket(int(row.home_goals), int(row.away_goals))
        for row in adjusted.itertuples(index=False)
    ]
    if bool(constraint.get("has_market_outcome_constraint", False)):
        adjusted = apply_market_probability_anchor(
            adjusted,
            category_column="outcome_bucket",
            target_probabilities={
                "home_win": float(constraint["market_home_win_probability"]),
                "draw": float(constraint["market_draw_probability"]),
                "away_win": float(constraint["market_away_win_probability"]),
            },
            weight=outcome_weight,
        )
    if bool(constraint.get("has_market_total_goals_constraint", False)):
        adjusted = apply_market_probability_anchor(
            adjusted,
            category_column="total_goals_bucket",
            target_probabilities=dict(constraint["market_total_goals_probabilities"]),
            weight=total_goals_weight,
        )
    return adjusted.drop(columns=["outcome_bucket", "total_goals_bucket"])


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
    market_constraints: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = enhanced_feature_columns()
    fixtures = add_group_match_rounds(
        fixture_features.sort_values(["date_et", "match_no"])
    ).head(limit)
    home_rates = clip_goal_rates(home_model.predict(fixtures[columns]))
    away_rates = clip_goal_rates(away_model.predict(fixtures[columns]))
    lineup_summary = lineup_adjustment_summary(
        pd.DataFrame() if predicted_lineups is None else predicted_lineups
    )
    market_constraints = pd.DataFrame() if market_constraints is None else market_constraints

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
        opener_adjustment = apply_group_opener_mismatch_adjustment(
            home_goal_rate=float(lineup_adjustment["home_expected_goals"]),
            away_goal_rate=float(lineup_adjustment["away_expected_goals"]),
            stage=row.stage,
            group_match_round=getattr(row, "group_match_round", None),
            elo_diff=getattr(row, "elo_diff", 0.0),
            home_team=str(row.home_team),
            away_team=str(row.away_team),
        )
        matrix = scoreline_matrix(
            float(opener_adjustment["home_expected_goals"]),
            float(opener_adjustment["away_expected_goals"]),
            max_goals=max_goals,
            rho=rho,
        )
        market_constraint = constraint_for_match(
            market_constraints,
            match_no=int(row.match_no),
        )
        matrix = apply_market_scoreline_constraints(matrix, market_constraint)
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
                    "home_expected_goals": float(opener_adjustment["home_expected_goals"]),
                    "away_expected_goals": float(opener_adjustment["away_expected_goals"]),
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
                    "group_match_round": getattr(row, "group_match_round", None),
                    "group_opener_mismatch_adjustment_applied": opener_adjustment[
                        "group_opener_mismatch_adjustment_applied"
                    ],
                    "group_opener_favorite_team": opener_adjustment[
                        "group_opener_favorite_team"
                    ],
                    "group_opener_favorite_elo_edge": opener_adjustment[
                        "group_opener_favorite_elo_edge"
                    ],
                    "home_group_opener_log_adjustment": opener_adjustment[
                        "home_group_opener_log_adjustment"
                    ],
                    "away_group_opener_log_adjustment": opener_adjustment[
                        "away_group_opener_log_adjustment"
                    ],
                    "has_market_outcome_constraint": bool(
                        market_constraint.get("has_market_outcome_constraint", False)
                    ),
                    "market_home_win_probability": market_constraint.get(
                        "market_home_win_probability"
                    ),
                    "market_draw_probability": market_constraint.get(
                        "market_draw_probability"
                    ),
                    "market_away_win_probability": market_constraint.get(
                        "market_away_win_probability"
                    ),
                    "has_market_total_goals_constraint": bool(
                        market_constraint.get("has_market_total_goals_constraint", False)
                    ),
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
    sporttery_market_odds_snapshots = (
        pd.read_parquet(SPORTTERY_MARKET_ODDS_SNAPSHOTS_PATH)
        if SPORTTERY_MARKET_ODDS_SNAPSHOTS_PATH.exists()
        else pd.DataFrame()
    )
    historical_features = build_historical_enhanced_features(matches)
    fixture_features = build_2026_enhanced_features(match_features, matches)
    market_constraints = build_scoreline_market_constraints(
        sporttery_market_odds_snapshots
    )

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
        market_constraints=market_constraints,
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
