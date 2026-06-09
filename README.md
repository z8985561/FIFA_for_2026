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
