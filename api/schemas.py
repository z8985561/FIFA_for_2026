from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    row_counts: dict[str, int]


class MetadataResponse(BaseModel):
    model_version: str
    data_scope: str
    row_counts: dict[str, int]
    latest_score_odds_fetched_at: str | None = None
    latest_market_fetched_at: str | None = None
    latest_match_date_et: str | None = None
    compliance_note: str


class MatchSummary(BaseModel):
    match_no: int
    stage: str | None = None
    group_name: str | None = None
    date_et: str | None = None
    time_et: str | None = None
    date_bj: str | None = None
    time_bj: str | None = None
    home_team: str
    away_team: str
    home_team_zh: str
    away_team_zh: str
    venue_city: str | None = None
    home_win_probability: float | None = None
    draw_probability: float | None = None
    away_win_probability: float | None = None
    predicted_outcome: str | None = None
    has_market_odds: bool = False
    latest_fetched_at: str | None = None
    top_scoreline: str | None = None
    top_scoreline_probability: float | None = None


class ScheduleMatch(BaseModel):
    match_no: int
    stage: str
    group_name: str | None = None
    date_et: str | None = None
    time_et: str | None = None
    date_bj: str | None = None
    time_bj: str | None = None
    home_team: str
    away_team: str
    home_team_zh: str
    away_team_zh: str
    venue: str | None = None
    city: str | None = None
    venue_city: str | None = None
    neutral: bool = True


class MatchDetail(BaseModel):
    match: MatchSummary
    expected_goals: dict[str, float | None]
    outcome_probabilities: dict[str, float | None]
    market_probabilities: dict[str, float | None]
    factor_breakdown: list[dict[str, float | str | bool | None]]


class ScorelineRow(BaseModel):
    match_no: int
    stage: str | None = None
    group_name: str | None = None
    date_et: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    home_team_zh: str | None = None
    away_team_zh: str | None = None
    scoreline_rank: int | None = None
    scoreline: str
    model_probability: float
    model_fair_odds: float | None = None
    best_decimal_odds: float | None = None
    average_decimal_odds: float | None = None
    market_edge: float | None = None
    kelly_fraction: float | None = None
    has_score_odds: bool = False
    value_signal: str = "missing_odds"
    bookmaker_count: int | None = None
    source_names: str | None = None
    source_urls: str | None = None
    source_match_ids: str | None = None
    latest_fetched_at: str | None = None


class GroupAdvanceRow(BaseModel):
    group_name: str
    team_name: str
    team_name_zh: str
    group_winner_probability: float
    group_runner_up_probability: float
    top2_probability: float
    third_place_advance_probability: float
    group_advance_probability: float
    not_advance_probability: float


class SimulatorSelection(BaseModel):
    match_no: int
    scoreline: str


class SimulatorRequest(BaseModel):
    budget: float = Field(gt=0)
    stake_per_combination: float = Field(default=2.0, gt=0)
    bet_type: str = "single"
    selections: list[SimulatorSelection]


class SimulatorCombination(BaseModel):
    selections: list[SimulatorSelection]
    hit_probability: float
    decimal_odds: float | None = None
    theoretical_payout: float | None = None
    expected_payout: float | None = None
    missing_odds: bool = False


class SimulatorResponse(BaseModel):
    budget: float
    stake_per_combination: float
    bet_type: str
    combination_count: int
    total_stake: float
    min_theoretical_payout: float | None
    max_theoretical_payout: float | None
    total_expected_payout: float
    expected_net_return: float
    estimated_hit_probability: float
    payout_spread_ratio: float | None
    risk_score: int
    risk_rating: str
    risk_reasons: list[str]
    combinations: list[SimulatorCombination]
