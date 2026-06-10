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
python -m src.enhanced_model
python -m src.scoreline_model
python -m src.tournament_simulator
python -m src.world_cup_backtest --years 2018 2022
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
