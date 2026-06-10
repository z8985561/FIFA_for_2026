# FIFA World Cup Win Probability Research

This workspace is prepared for World Cup match win probability research on Windows.

## Planning Docs

- Data collection plan: [docs/data_collection_plan.md](docs/data_collection_plan.md)
- Scoreline data enhancement plan:
  [docs/scoreline_data_enhancement_plan.md](docs/scoreline_data_enhancement_plan.md)

## Environment

- Python `3.11`
- Virtual environment in `.venv`
- Dependency management through `pip`
- Project metadata in `pyproject.toml`

## Quick Start

```powershell
.venv\Scripts\Activate.ps1
python --version
python -m jupyter lab
```

## Docker Quick Start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

After startup:

- JupyterLab: `http://localhost:8888`
- Postgres: `localhost:5432`
- Default token: value from `JUPYTER_TOKEN` in `.env`

To stop the stack:

```powershell
docker compose down
```

## Project Layout

```text
data/
  raw/
  processed/
  features/
notebooks/
reports/
src/
tests/
```

## Recommended First Steps

1. Put historical match data into `data/raw/`.
2. Create feature engineering code in `src/`.
3. Use `notebooks/` for exploration and model diagnostics.
4. Save plots and experiment outputs in `reports/`.

## Useful Commands

```powershell
.venv\Scripts\Activate.ps1
python -m pip list
python -m src.data_pipeline
python -m src.baseline_model
python -m src.postgres_sync
python -m src.postgres_views
python -m src.world_cup_identity
python -m src.goal_form_features
python -m src.feature_store
python -m src.odds_pipeline
python -m src.lineups_pipeline
python -m src.enhanced_model
python -m src.scoreline_model
python -m src.tournament_simulator
python -m src.world_cup_backtest --years 2018 2022
python -m src.analysis_diagnostics
python -m src.postgres_sync
python -m src.postgres_queries top-rated --limit 10
python -m src.postgres_queries match-features --team Argentina
python -m src.postgres_queries enhanced-prediction-query --team Argentina
python -m src.postgres_queries scoreline-query --match-no 1 --limit 10
python -m src.postgres_queries world-cup-teams --limit 10
python -m src.postgres_queries squad --team Argentina
python -m src.postgres_queries squad-composition --team Argentina
python -m src.postgres_queries goal-form --team Argentina
python -m src.postgres_queries team-schedule-difficulty --team Argentina
python -m src.postgres_queries group-difficulty --limit 12
python -m src.postgres_queries team-summary --team Argentina
python -m src.postgres_queries prediction-query --team Brazil --limit 5
python -m src.postgres_queries group-overview --group-name "Group C"
python -m src.postgres_queries group-strength --group-name "Group C"
python -m src.postgres_queries prediction-extremes --mode balanced --limit 8
python -m src.research_report team --team Argentina
python -m src.research_report group --group-name "Group C"
python -m src.research_report world-cup-pack
python -m pytest
python -m ruff check .
python -m jupyter lab
docker compose up --build
docker compose down
```

## MVP Workflow

1. Download and normalize historical match data:

```powershell
.venv\Scripts\Activate.ps1
python -m src.data_pipeline
```

2. Train the baseline win-probability model and generate 2026 predictions:

```powershell
.venv\Scripts\Activate.ps1
python -m src.baseline_model
python -m src.enhanced_model
python -m src.postgres_sync
```

Outputs are written to:

- `data/raw/`
- `data/processed/`
- `reports/`

## Enhanced Model

Build a historical feature store with recent-form features, train the enhanced model, and
generate 2026 group-stage predictions:

```powershell
.venv\Scripts\Activate.ps1
python -m src.enhanced_model
```

Outputs:

- `data/features/historical_match_feature_store.parquet`
- `reports/enhanced_model_metrics.json`
- `reports/world_cup_2026_enhanced_predictions.csv`

## Tournament Simulation

Run a Monte Carlo simulation from group stage through the final:

```powershell
.venv\Scripts\Activate.ps1
python -m src.tournament_simulator --simulations 10000 --seed 20260609
```

Output:

- `reports/world_cup_2026_tournament_simulation.csv`

The first simulator version uses enhanced model probabilities for group-stage matches and
neutral-field Elo probabilities for knockout advancement. It implements 12 groups, best eight
third-place teams, and a deterministic Round-of-32 third-place slot assignment. The third-place
slot assignment should be replaced with the full official allocation table once encoded.

## World Cup Backtest

Run independent tournament backtests for completed World Cups:

```powershell
.venv\Scripts\Activate.ps1
python -m src.world_cup_backtest --years 2018 2022
```

Outputs:

- `reports/world_cup_backtest_metrics.csv`
- `reports/world_cup_backtest_predictions.csv`

The backtest trains only on matches before each World Cup start date, filters the validation
set to `FIFA World Cup` finals matches, and reports group-stage and knockout-stage metrics
separately using 90-minute scorelines.

Build diagnostic slices on top of the backtest predictions:

```powershell
.venv\Scripts\Activate.ps1
python -m src.analysis_diagnostics
```

Outputs:

- `reports/world_cup_backtest_calibration.csv`
- `reports/world_cup_backtest_confederation_diagnostics.csv`
- `reports/world_cup_backtest_low_score_diagnostics.csv`
- `reports/world_cup_backtest_upset_diagnostics.csv`

These reports break down top-class calibration, confederation matchup performance,
high-confidence misses, and knockout low-score draw coverage.

## Scoreline Model

Train Poisson goal models and generate exact-score probabilities for upcoming fixtures:

```powershell
.venv\Scripts\Activate.ps1
python -m src.scoreline_model --limit 4 --top-scores 10
```

Outputs:

- `reports/scoreline_model_metrics.json`
- `reports/world_cup_2026_scoreline_analysis.csv`

This scoreline model predicts each team's expected goals from the same historical recent-form
feature store used by the enhanced win-probability model, then applies a Dixon-Coles low-score
correlation correction. It should later be improved with xG, shot quality, player availability,
odds, and weather calibration.

## Correct Score Odds

Collect publicly available correct-score odds and compare them against the model probabilities:

```powershell
.venv\Scripts\Activate.ps1
python -m src.score_odds_pipeline --limit 72
python -m src.value_bets_report --limit 4
```

Outputs:

- `data/processed/score_odds_snapshots.parquet`
- `data/features/score_odds_features.parquet`
- `data/processed/score_odds_collection_status.parquet`
- `reports/scoreline_value_bets.csv`

The collector discovers China Sports Lottery football matches from the public match-list API
behind `https://www.lottery.gov.cn/jc/index.html`, keeps only rows where the league is `世界杯`,
then collects fixed-bonus correct-score odds from each Sporttery detail page `mid`.

For incremental scans, keep existing Sporttery `mid` rows and only fill newly discovered matches:

```powershell
python -m src.score_odds_pipeline --limit 72 --skip-existing-sporttery
```

For live market monitoring, append every run into the historical score-odds snapshot file:

```powershell
python -m src.score_odds_pipeline --limit 72 --append-history
```

Rows keep `source_name`, `source_url`, and `source_match_id`, so Postgres reports can distinguish
`中国体育彩票` from international public odds and can use the Sporttery `mid` to detect already
collected matches. If the Sporttery home/away order differs from the local fixture order, exact
score labels are reversed before storage.

## Postgres Sync

With the Docker database running, sync processed data into Postgres:

```powershell
.venv\Scripts\Activate.ps1
python -m src.postgres_sync
```

Default connection settings are read from `.env`.

## World Cup Identity Collection

Build the first identity-layer dataset for all 48 qualified teams:

```powershell
.venv\Scripts\Activate.ps1
python -m src.world_cup_identity
```

Outputs:

- `data/processed/fifa_rankings_2026.parquet`
- `data/processed/squads_2026.parquet`
- `data/processed/world_cup_teams_2026.parquet`

## Match Feature Store

Build model-ready features for known 2026 fixtures:

```powershell
.venv\Scripts\Activate.ps1
python -m src.feature_store
```

Output:

- `data/features/match_feature_store_2026.parquet`

## Predicted Lineups

Build the first predicted-lineup layer for the opening known group-stage matches:

```powershell
.venv\Scripts\Activate.ps1
python -m src.lineups_pipeline
python -m src.postgres_sync
python -m src.postgres_views
```

Output:

- `data/processed/predicted_lineups.parquet`

The current lineup layer is explicitly marked as `lineup_status = predicted`; official
confirmed lineups should be added closer to kickoff when they are released. The Postgres view
`research.predicted_lineup_summary` exposes Chinese team names and source URLs for quick review.

## Odds Pipeline

Build processed bookmaker snapshots and consensus match-odds features from raw odds API dumps:

```powershell
.venv\Scripts\Activate.ps1
python -m src.odds_pipeline
```

Outputs:

- `data/processed/market_odds_snapshots.parquet`
- `data/features/match_odds_features.parquet`

The first pipeline version ingests `h2h` bookmaker odds from `data/raw/odds/`, preserves
bookmaker-level snapshots, removes overround from 1X2 prices, and builds consensus implied
probabilities per match for downstream model features.

Historical odds can be staged separately under `data/raw/odds/historical/` and converted into
the backtest feature file:

```powershell
.venv\Scripts\Activate.ps1
python -m src.odds_pipeline --historical --raw-dir data/raw/odds/historical
python -m src.world_cup_backtest --years 2018 2022
```

If odds are available as a manually curated CSV, use the same pipeline with `--manual-csv`:

```powershell
.venv\Scripts\Activate.ps1
python -m src.odds_pipeline --historical --manual-csv data/raw/odds/historical/manual_1x2_odds.csv
python -m src.world_cup_backtest --years 2018 2022
```

Manual CSV required columns:

- `match_date`
- `home_team`
- `away_team`
- `home_win_odds`
- `draw_odds`
- `away_win_odds`

Optional columns include `bookmaker_key`, `bookmaker_title`, `event_id`, `commence_time`, and
`fetched_at`.

When `data/features/historical_match_odds_features.parquet` exists, the World Cup backtest
adds bookmaker-only (`market_outcome_*`) and model-market blend (`blended_outcome_*`) metrics.
If historical odds are absent, the backtest still runs and reports `market_odds_coverage = 0`.

## Postgres Views

Create reusable SQL views in Postgres after syncing data:

```powershell
.venv\Scripts\Activate.ps1
python -m src.postgres_views
```

## Postgres Query CLI

Run common research queries without writing SQL manually:

```powershell
.venv\Scripts\Activate.ps1
python -m src.postgres_queries top-rated --limit 10
python -m src.postgres_queries team-history --team Argentina --limit 5
python -m src.postgres_queries fixtures --stage "Group Stage" --limit 8
python -m src.postgres_queries head-to-head --team-a Brazil --team-b Argentina
python -m src.postgres_queries competition-summary --competition-type world_cup
python -m src.postgres_queries team-summary --team Argentina
python -m src.postgres_queries prediction-query --group-name "Group C" --limit 6
python -m src.postgres_queries enhanced-prediction-query --group-name "Group C" --limit 6
python -m src.postgres_queries scoreline-query --group-name "Group A" --limit 20
python -m src.postgres_queries group-overview --group-name "Group C"
python -m src.postgres_queries top-rated --limit 20 --output reports/top_rated.csv
python -m src.postgres_queries recent-form --team Brazil --limit 8
python -m src.postgres_queries goal-form --team Brazil --limit 1
python -m src.postgres_queries team-vs-field --team Argentina
python -m src.postgres_queries group-strength --group-name "Group C"
python -m src.postgres_queries prediction-extremes --mode lopsided --stage "Group Stage" --limit 6
python -m src.postgres_queries world-cup-teams --group-name "Group C"
python -m src.postgres_queries squad --team Argentina --position FW
python -m src.postgres_queries squad-summary --team Argentina
python -m src.postgres_queries group-profiles --group-name "Group C"
python -m src.postgres_queries squad-composition --team Argentina
python -m src.postgres_queries team-schedule-difficulty --team Argentina
python -m src.postgres_queries group-difficulty --limit 12
python -m src.postgres_queries match-features --group-name "Group C"
python -m src.research_report team --team Argentina --output reports/team_report_argentina.md
python -m src.research_report group --group-name "Group C" --output reports/group_report_group_c.md
python -m src.research_report world-cup-pack --output-dir reports/world_cup_2026_pack
```

## Research Report CLI

Generate reusable Markdown reports on top of the Postgres research queries:

```powershell
.venv\Scripts\Activate.ps1
python -m src.research_report team --team Argentina
python -m src.research_report group --group-name "Group C"
```

Default outputs:

- `reports/team_report_<team>.md`
- `reports/group_report_<group>.md`
- `reports/team_report_<team>_assets/`
- `reports/group_report_<group>_assets/`

Batch research pack:

```powershell
.venv\Scripts\Activate.ps1
python -m src.research_report world-cup-pack
python -m src.research_report world-cup-pack --include-team-reports
```

Default pack output:

- `reports/world_cup_2026_pack/index.md`
- `reports/world_cup_2026_pack/groups/`
- `reports/world_cup_2026_pack/charts/`
- `reports/world_cup_2026_pack/teams/` when `--include-team-reports` is enabled

Single team and group reports also generate embedded chart assets next to the Markdown report. The generated pack `index.md` includes tournament-level summaries for group strength, the most balanced or lopsided group-stage matches, and chart assets embedded from `reports/world_cup_2026_pack/charts/`.
