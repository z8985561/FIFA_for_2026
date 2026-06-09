# FIFA World Cup Win Probability Research

This workspace is prepared for World Cup match win probability research on Windows.

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
python -m src.postgres_queries top-rated --limit 10
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
python -m src.postgres_sync
```

Outputs are written to:

- `data/raw/`
- `data/processed/`
- `reports/`

## Postgres Sync

With the Docker database running, sync processed data into Postgres:

```powershell
.venv\Scripts\Activate.ps1
python -m src.postgres_sync
```

Default connection settings are read from `.env`.

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
python -m src.postgres_queries group-overview --group-name "Group C"
python -m src.postgres_queries top-rated --limit 20 --output reports/top_rated.csv
python -m src.postgres_queries recent-form --team Brazil --limit 8
python -m src.postgres_queries team-vs-field --team Argentina
python -m src.postgres_queries group-strength --group-name "Group C"
python -m src.postgres_queries prediction-extremes --mode lopsided --stage "Group Stage" --limit 6
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

Batch research pack:

```powershell
.venv\Scripts\Activate.ps1
python -m src.research_report world-cup-pack
python -m src.research_report world-cup-pack --include-team-reports
```

Default pack output:

- `reports/world_cup_2026_pack/index.md`
- `reports/world_cup_2026_pack/groups/`
- `reports/world_cup_2026_pack/teams/` when `--include-team-reports` is enabled
