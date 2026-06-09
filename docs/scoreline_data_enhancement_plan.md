# Scoreline Data Enhancement Plan

This plan tracks the next data layers for improving exact-score probabilities beyond the current
Poisson plus Dixon-Coles baseline.

## Current Baseline

- Historical national-team scores from `matches.parquet`
- Elo and expected win features
- Recent form features from the last 5 and 10 matches
- Fixture rest-day context for 2026 group-stage matches
- Poisson goal models for home and away expected goals
- Dixon-Coles low-score correction estimated from historical training matches

## Priority Data

| Priority | Data | Why It Helps | Candidate Sources |
|---|---|---|---|
| P0 | Team goal-form features | Already available locally and directly supports attack/defense rates | `matches.parquet` |
| P0 | 2026 fixture rest and venue context | Captures fatigue and tournament schedule effects | `fixtures_2026.parquet` |
| P1 | xG, shots, shots on target | Better estimates goal creation and concession quality | StatsBomb Open Data, API-Football, SportMonks |
| P1 | Over/under, BTTS, correct-score odds | Calibrates total-goal and exact-score distributions | The Odds API, API-Football odds |
| P1 | Expected lineups and injuries | Captures single-match player availability shocks | FIFA match centre, SportMonks, Transfermarkt |
| P2 | Weather and altitude | Refines pace and scoring environment | Open-Meteo, venue metadata |
| P2 | Referee profile | Helps model cards, penalties, and match volatility | FIFA officials, WorldReferee |

## Suggested Tables

### `team_goal_form_features`

- `team_id`
- `as_of_date`
- `goals_for_last_5`
- `goals_against_last_5`
- `goals_for_last_10`
- `goals_against_last_10`
- `clean_sheet_rate_last_10`
- `btts_rate_last_10`
- `avg_total_goals_last_10`

### `match_shot_xg_stats`

- `match_id`
- `team_id`
- `shots`
- `shots_on_target`
- `xg`
- `non_penalty_xg`
- `big_chances`
- `box_shots`
- `set_piece_xg`
- `source`

### `market_goal_odds`

- `match_no`
- `bookmaker`
- `captured_at`
- `over_2_5_odds`
- `under_2_5_odds`
- `btts_yes_odds`
- `btts_no_odds`
- `correct_score_json`
- `overround`

### `player_availability`

- `player_id`
- `team_id`
- `as_of_date`
- `status`
- `injury_type`
- `expected_minutes`
- `is_likely_starter`
- `source_url`

## Next Implementation Steps

1. Materialize `team_goal_form_features` from existing historical matches.
2. Add optional market-goal-odds ingestion once an API/source is selected.
3. Add xG and shot feature ingestion for competitions with reliable coverage.
4. Calibrate scoreline outputs against over/under and BTTS market probabilities.
5. Add late-stage lineup, injury, weather, and referee adjustments close to matchday.
