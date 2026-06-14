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
  actual_home_score?: number | null
  actual_away_score?: number | null
  completed: boolean
  result_source_name?: string | null
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
  actual_home_score?: number | null
  actual_away_score?: number | null
  completed: boolean
  result_source_name?: string | null
  predicted_outcome?: string | null
  home_win_probability?: number | null
  draw_probability?: number | null
  away_win_probability?: number | null
  top_scoreline?: string | null
  top_scoreline_probability?: number | null
}

export interface DataQualityRow {
  match_no: number
  stage: string
  group_name?: string | null
  home_team: string
  away_team: string
  home_team_zh: string
  away_team_zh: string
  has_fixture: boolean
  has_prediction: boolean
  has_scoreline_model: boolean
  has_score_odds: boolean
  has_market_odds: boolean
  has_lineup_adjustment: boolean
  latest_score_odds_fetched_at?: string | null
  latest_market_fetched_at?: string | null
  completeness_score: number
  completeness_level: 'High' | 'Medium' | 'Low'
  missing_items: readonly string[]
}

export interface FactorBreakdown {
  factor: string
  home_delta_goals?: number | null
  away_delta_goals?: number | null
  applied?: boolean | null
  description: string
}

export interface TeamContext {
  team_name: string
  team_name_zh: string
  coach_name_zh?: string | null
  coach_name_en?: string | null
  suspended_count: number
  suspended_players_zh: readonly string[]
  suspended_players_en: readonly string[]
  squad_size?: number | null
}

export interface MatchPreviewSource {
  match_no: number
  team_name: string
  team_name_zh: string
  source_name?: string | null
  source_domain?: string | null
  source_title?: string | null
  source_url?: string | null
  published_time?: string | null
  predicted_lineup_text?: string | null
  injury_notes?: string | null
  coach_quotes?: string | null
  key_player_notes?: string | null
}

export interface MatchTechStats {
  home_possession: number
  away_possession: number
  home_shots: number
  away_shots: number
  home_shots_on_target: number
  away_shots_on_target: number
  home_corners: number
  away_corners: number
  home_yellow_cards: number
  away_yellow_cards: number
  home_red_cards: number
  away_red_cards: number
}

export interface MatchDetail {
  match: MatchSummary
  expected_goals: Record<string, number | null>
  outcome_probabilities: Record<string, number | null>
  market_probabilities: Record<string, number | null>
  home_team_context?: TeamContext | null
  away_team_context?: TeamContext | null
  preview_sources: MatchPreviewSource[]
  match_tech?: MatchTechStats | null
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
  standing_rank: number
  played: number
  wins: number
  draws: number
  losses: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
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

export interface SimulatorCombination {
  selections: SimulatorSelection[]
  hit_probability: number
  decimal_odds?: number | null
  theoretical_payout?: number | null
  expected_payout?: number | null
  missing_odds: boolean
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
  combinations: SimulatorCombination[]
}

export interface MatchReviewRow {
  match_no: number
  stage?: string | null
  group_name?: string | null
  home_team: string
  away_team: string
  home_team_zh: string
  away_team_zh: string
  predicted_outcome?: string | null
  actual_outcome?: string | null
  top_scoreline?: string | null
  actual_scoreline?: string | null
  expected_home_goals?: number | null
  expected_away_goals?: number | null
  expected_total_goals?: number | null
  actual_total_goals?: number | null
  outcome_hit: boolean
  scoreline_hit: boolean
  total_goals_error?: number | null
  actual_outcome_probability?: number | null
  predicted_home_win_probability?: number | null
  predicted_draw_probability?: number | null
  predicted_away_win_probability?: number | null
  review_bucket: string
  result_source_name?: string | null
}

export interface TeamCompareItem {
  team_name: string
  team_name_zh: string
  elo?: number | null
  fifa_rank?: number | null
  squad_size?: number | null
  average_age?: number | null
  total_caps?: number | null
  group_advance_probability?: number | null
  avg_goals_scored?: number | null
  avg_goals_conceded?: number | null
  avg_shots?: number | null
  avg_fouls?: number | null
  avg_yellow_cards?: number | null
  avg_red_cards?: number | null
}

export interface TeamCompareResponse {
  team_a: TeamCompareItem
  team_b: TeamCompareItem
}



export interface TeamProfileSquadPlayer {
  shirt_no: string
  player_name: string
  player_name_zh: string
  position: string
  age: number
  goals: number
  assists: number
  yellow_cards: number
  red_cards: number
  is_suspended: boolean
}

export interface TeamProfileResponse {
  team_name: string
  team_name_zh: string
  group_name: string
  confederation: string
  fifa_rank?: number | null
  elo?: number | null
  matches_played: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  group_advance_probability?: number | null
  stage_probabilities: Record<string, number>
  recent_form: readonly string[]
  completed_matches: ReadonlyArray<{
    match_no: number
    home_team: string
    away_team: string
    home_team_zh: string
    away_team_zh: string
    date_et?: string | null
    is_home: boolean
    completed: boolean
    home_score?: number | null
    away_score?: number | null
  }>
  upcoming_matches: ReadonlyArray<{
    match_no: number
    home_team: string
    away_team: string
    home_team_zh: string
    away_team_zh: string
    date_et?: string | null
    is_home: boolean
    completed: boolean
  }>
  squad: readonly TeamProfileSquadPlayer[]
  tournament_stats: Record<string, number | null>
}
