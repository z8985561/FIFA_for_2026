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
    actual_home_score: int | None = None
    actual_away_score: int | None = None
    completed: bool = False
    result_source_name: str | None = None


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
    actual_home_score: int | None = None
    actual_away_score: int | None = None
    completed: bool = False
    result_source_name: str | None = None
    predicted_outcome: str | None = None
    home_win_probability: float | None = None
    draw_probability: float | None = None
    away_win_probability: float | None = None
    top_scoreline: str | None = None
    top_scoreline_probability: float | None = None


class DataQualityRow(BaseModel):
    match_no: int
    stage: str
    group_name: str | None = None
    home_team: str
    away_team: str
    home_team_zh: str
    away_team_zh: str
    has_fixture: bool
    has_prediction: bool
    has_scoreline_model: bool
    has_score_odds: bool
    has_market_odds: bool
    has_lineup_adjustment: bool
    latest_score_odds_fetched_at: str | None = None
    latest_market_fetched_at: str | None = None
    completeness_score: int
    completeness_level: str
    missing_items: list[str]


class TeamContext(BaseModel):
    team_name: str
    team_name_zh: str
    coach_name_zh: str | None = None
    coach_name_en: str | None = None
    suspended_count: int = 0
    suspended_players_zh: list[str] = []
    suspended_players_en: list[str] = []
    squad_size: int | None = None


class MatchPreviewSource(BaseModel):
    match_no: int
    team_name: str
    team_name_zh: str
    source_name: str | None = None
    source_domain: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    published_time: str | None = None
    predicted_lineup_text: str | None = None
    injury_notes: str | None = None
    coach_quotes: str | None = None
    key_player_notes: str | None = None


class MatchTechStats(BaseModel):
    home_possession: int = 0
    away_possession: int = 0
    home_shots: int = 0
    away_shots: int = 0
    home_shots_on_target: int = 0
    away_shots_on_target: int = 0
    home_corners: int = 0
    away_corners: int = 0
    home_yellow_cards: int = 0
    away_yellow_cards: int = 0
    home_red_cards: int = 0
    away_red_cards: int = 0


class MatchDetail(BaseModel):
    match: MatchSummary
    expected_goals: dict[str, float | None]
    outcome_probabilities: dict[str, float | None]
    market_probabilities: dict[str, float | None]
    home_team_context: TeamContext | None = None
    away_team_context: TeamContext | None = None
    preview_sources: list[MatchPreviewSource] = []
    match_tech: MatchTechStats | None = None
    factor_breakdown: list[dict[str, float | str | bool | None]]


class MatchReviewRow(BaseModel):
    match_no: int
    stage: str | None = None
    group_name: str | None = None
    home_team: str
    away_team: str
    home_team_zh: str
    away_team_zh: str
    predicted_outcome: str | None = None
    actual_outcome: str | None = None
    top_scoreline: str | None = None
    actual_scoreline: str | None = None
    expected_home_goals: float | None = None
    expected_away_goals: float | None = None
    expected_total_goals: float | None = None
    actual_total_goals: int | None = None
    outcome_hit: bool = False
    scoreline_hit: bool = False
    total_goals_error: float | None = None
    actual_outcome_probability: float | None = None
    predicted_home_win_probability: float | None = None
    predicted_draw_probability: float | None = None
    predicted_away_win_probability: float | None = None
    review_bucket: str
    result_source_name: str | None = None


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
    standing_rank: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
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
