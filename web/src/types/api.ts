export interface HealthResponse {
  status: string
  row_counts: Record<string, number>
}

export interface MetadataResponse {
  model_version: string
  data_scope: string
  row_counts: Record<string, number>
  latest_score_odds_fetched_at?: string | null
  latest_market_fetched_at?: string | null
  latest_match_date_et?: string | null
  compliance_note: string
}

export interface MatchSummary {
  match_no: number
  stage?: string | null
  group_name?: string | null
  date_et?: string | null
  time_et?: string | null
  date_bj?: string | null
  time_bj?: string | null
  home_team: string
  away_team: string
  home_team_zh: string
  away_team_zh: string
  venue_city?: string | null
  home_win_probability?: number | null
  draw_probability?: number | null
  away_win_probability?: number | null
  predicted_outcome?: string | null
  has_market_odds: boolean
  latest_fetched_at?: string | null
  top_scoreline?: string | null
  top_scoreline_probability?: number | null
}

export interface ScheduleMatch {
  match_no: number
  stage: string
  group_name?: string | null
  date_et?: string | null
  time_et?: string | null
  date_bj?: string | null
  time_bj?: string | null
  home_team: string
  away_team: string
  home_team_zh: string
  away_team_zh: string
  venue?: string | null
  city?: string | null
  venue_city?: string | null
  neutral: boolean
}

export interface FactorBreakdown {
  factor: string
  home_delta_goals?: number | null
  away_delta_goals?: number | null
  applied?: boolean | null
  description: string
}

export interface MatchDetail {
  match: MatchSummary
  expected_goals: Record<string, number | null>
  outcome_probabilities: Record<string, number | null>
  market_probabilities: Record<string, number | null>
  factor_breakdown: FactorBreakdown[]
}

export interface ScorelineRow {
  match_no: number
  stage?: string | null
  group_name?: string | null
  date_et?: string | null
  home_team?: string | null
  away_team?: string | null
  home_team_zh?: string | null
  away_team_zh?: string | null
  scoreline_rank?: number | null
  scoreline: string
  model_probability: number
  model_fair_odds?: number | null
  best_decimal_odds?: number | null
  average_decimal_odds?: number | null
  market_edge?: number | null
  kelly_fraction?: number | null
  has_score_odds: boolean
  value_signal: string
  bookmaker_count?: number | null
  source_names?: string | null
  source_urls?: string | null
  source_match_ids?: string | null
  latest_fetched_at?: string | null
}

export interface GroupAdvanceRow {
  group_name: string
  team_name: string
  team_name_zh: string
  group_winner_probability: number
  group_runner_up_probability: number
  top2_probability: number
  third_place_advance_probability: number
  group_advance_probability: number
  not_advance_probability: number
}

export interface SimulatorSelection {
  match_no: number
  scoreline: string
}

export interface SimulatorResponse {
  budget: number
  stake_per_combination: number
  bet_type: string
  combination_count: number
  total_stake: number
  min_theoretical_payout?: number | null
  max_theoretical_payout?: number | null
  total_expected_payout: number
  expected_net_return: number
  estimated_hit_probability: number
  payout_spread_ratio?: number | null
  risk_score: number
  risk_rating: string
  risk_reasons: string[]
}
