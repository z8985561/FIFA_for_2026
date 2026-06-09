# World Cup Data Collection Plan

This document defines the recommended data scope for the FIFA World Cup win-probability project.

## Goal

Build a complete research dataset for all 48 World Cup teams that supports:

- match win/draw/loss probability modeling
- group-stage and knockout-stage simulation
- team and group scouting reports
- feature engineering for classical ML and probabilistic models

## Collection Principles

- Prefer official or primary sources for identities, squads, fixtures, rankings, and tournament metadata.
- Store raw data separately from cleaned analytics tables.
- Use stable keys such as `team_id`, `player_id`, `match_id`.
- Normalize encodings to UTF-8 and keep a team-name mapping dictionary.
- Record fetch timestamp, source URL, and source version for every ingestion job.

## Priority Tiers

### P0 Must Have

These datasets are required for a credible baseline model.

1. Team master data
2. World Cup final squads
3. Historical national-team matches
4. World Cup fixture and venue context
5. Latest team strength snapshots

### P1 High Value

These datasets should materially improve model quality.

1. Team match technical stats
2. Player recent form and availability
3. Squad structure features
4. Market odds
5. Travel and rest features

### P2 Nice to Have

These datasets are useful once the core pipeline is stable.

1. Weather
2. Tactical labels
3. Referee assignments
4. Media sentiment or news-derived signals

## Recommended Tables

### `teams`

One row per national team.

Suggested fields:

- `team_id`
- `team_name`
- `team_slug`
- `fifa_code`
- `confederation`
- `country_name`
- `world_cup_group`
- `coach_name`
- `fifa_rank`
- `fifa_points`
- `elo_rating`
- `world_cup_appearances`
- `last_updated_at`

### `players`

One row per player identity.

Suggested fields:

- `player_id`
- `player_name`
- `date_of_birth`
- `age`
- `height_cm`
- `preferred_foot`
- `primary_position`
- `secondary_position`
- `current_club`
- `current_league`
- `national_team_id`
- `last_updated_at`

### `squads_2026`

One row per player selected into a final World Cup squad.

Suggested fields:

- `squad_id`
- `team_id`
- `player_id`
- `shirt_number`
- `position_group`
- `captain_flag`
- `caps_before_tournament`
- `goals_before_tournament`
- `minutes_last_90_days`
- `injury_status`
- `source_url`
- `fetched_at`

### `matches`

Historical and tournament matches.

Suggested fields:

- `match_id`
- `match_date`
- `competition_name`
- `competition_type`
- `stage`
- `home_team_id`
- `away_team_id`
- `home_score`
- `away_score`
- `neutral_flag`
- `venue_name`
- `city`
- `country`
- `kickoff_local`
- `kickoff_utc`
- `attendance`
- `referee_name`
- `source_url`

### `team_match_stats`

Team-level stats per match.

Suggested fields:

- `match_id`
- `team_id`
- `opponent_team_id`
- `xg`
- `xga`
- `shots`
- `shots_on_target`
- `possession_pct`
- `passes_completed`
- `corners`
- `fouls`
- `yellow_cards`
- `red_cards`
- `ppda`
- `set_piece_goals`
- `open_play_goals`

### `player_recent_form`

Rolling form features built from club and national-team minutes.

Suggested fields:

- `player_id`
- `as_of_date`
- `minutes_last_30_days`
- `minutes_last_60_days`
- `minutes_last_90_days`
- `starts_last_10_matches`
- `goals_last_10_matches`
- `assists_last_10_matches`
- `injury_days_last_180_days`
- `availability_flag`

### `world_cup_fixtures`

Tournament fixture context for modeling and simulation.

Suggested fields:

- `match_no`
- `stage`
- `group_name`
- `date_local`
- `time_local`
- `date_utc`
- `home_team_id`
- `away_team_id`
- `venue_name`
- `city`
- `country`
- `rest_days_home`
- `rest_days_away`
- `travel_km_home`
- `travel_km_away`
- `timezone_shift_home`
- `timezone_shift_away`

### `market_odds`

Consensus or book-level odds snapshots.

Suggested fields:

- `odds_id`
- `match_id`
- `bookmaker`
- `captured_at`
- `home_win_odds`
- `draw_odds`
- `away_win_odds`
- `asian_handicap`
- `over_under_line`
- `over_odds`
- `under_odds`

## Feature Groups To Prioritize

### Team Strength

- Elo difference
- FIFA rank difference
- FIFA points difference
- squad market value difference
- coach tenure

### Form

- points per match over last 5 and 10 matches
- goal difference over last 5 and 10 matches
- xG difference over last 5 and 10 matches
- performance split by competition type

### Squad Quality

- average age
- average caps
- share of players in top European leagues
- goalkeeper experience
- defender height profile
- recent minutes concentration among expected starters

### Match Context

- rest day difference
- travel distance difference
- host-country advantage
- weather severity
- altitude

### Market Signal

- closing odds implied probabilities
- movement from opening to closing odds

## Recommended Sources

### Official Sources

- FIFA World Cup 2026 squads confirmed
  - [https://www.fifa.com/en/articles/fifa-world-cup-2026-squads-confirmed](https://www.fifa.com/en/articles/fifa-world-cup-2026-squads-confirmed)
  - Search result seen on 2026-06-09 indicated publication "last week"
- FIFA World Cup 2026 schedule and venues
  - [https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums)
  - Search result seen on 2026-06-09 indicated publication about 2 months earlier
- FIFA/Coca-Cola Men's World Ranking
  - [https://inside.fifa.com/en/fifa-world-ranking/ENG?gender=men](https://inside.fifa.com/en/fifa-world-ranking/ENG?gender=men)
  - Search result seen on 2026-06-09 indicated the last official update was 2026-04-01

### Secondary Sources

- Transfermarkt team and squad market values
- FBref team match logs and advanced match stats
- football-data.org for structured fixtures and odds where available

## Collection Roadmap

### Phase 1

Build identity and tournament tables.

1. `teams`
2. `world_cup_fixtures`
3. `players`
4. `squads_2026`

### Phase 2

Backfill performance history.

1. `matches`
2. `team_match_stats`
3. team-level rolling features

### Phase 3

Add player and market context.

1. `player_recent_form`
2. `market_odds`
3. travel and weather features

## Data Quality Rules

- All text fields stored as UTF-8.
- Build `team_name_aliases` for names like `USA` vs `United States` and `Curaçao` vs ASCII fallback forms.
- Reject duplicate `match_id` rows.
- Validate every World Cup group has exactly 4 teams.
- Validate every final squad has exactly 26 players unless an official exception exists.
- Store raw extracts under `data/raw/` before transformation.
- Log row counts and null-rate checks after every sync.

## Suggested Implementation Tasks

1. Add a `docs/source_registry.md` file listing each source, access pattern, and refresh cadence.
2. Add new raw landing folders under `data/raw/teams/`, `data/raw/players/`, `data/raw/odds/`.
3. Create schema modules for the new tables in `src/schema.py`.
4. Add ingestion scripts for FIFA team, squad, and ranking pages first.
5. Add tests for team-name normalization and squad integrity.

## Immediate Next Step

Start with three ingestion jobs:

1. FIFA rankings snapshot
2. FIFA final squad ingestion
3. Team master table assembly

Those three jobs will give the project a stable identity layer for all later data collection.
