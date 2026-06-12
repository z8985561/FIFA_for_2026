# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication

Always respond to the user in Chinese (中文).

## What this is

A FIFA World Cup 2026 match win-probability research project. Three layers that share data through files on disk:

1. **Python pipeline + models** (`src/`) — ingests historical results, builds Elo/form/odds features, trains win-probability and scoreline models, writes outputs to `data/` and `reports/`.
2. **FastAPI backend** (`api/`) — serves the dashboard. It reads the model **output files** (CSV/parquet in `reports/` and `data/`), not Postgres.
3. **Vue 3 dashboard** (`web/`) — TypeScript + Element Plus + ECharts + Pinia, consumes the API.

Windows-first: all workflows assume PowerShell and the `.venv` virtual environment.

## Common commands

```powershell
# Activate the environment first (required for every Python command)
.venv\Scripts\Activate.ps1

# Python tests / lint
python -m pytest                                  # all tests
python -m pytest tests/test_scoreline_model.py    # one file
python -m pytest tests/test_scoreline_model.py::test_name -q   # one test
python -m ruff check .                            # lint (line-length 100, rules E/F/I/UP/B)
python -m ruff format .                           # format

# Run the API (terminal 1)
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Run the dashboard (terminal 2)
cd web
npm install
npm run dev          # http://127.0.0.1:5173, proxies /api -> 127.0.0.1:8000
npm run build        # vue-tsc --noEmit type-check THEN vite build
```

Every pipeline/model/CLI module is invoked as `python -m src.<module>` (e.g. `python -m src.enhanced_model`). The README documents the full catalog of modules and `postgres_queries`/`research_report` subcommands.

## Pipeline data flow (the big picture)

Modules are chained by Python imports, not by an orchestrator. Running a downstream module re-derives its upstream inputs in-process via functions like `prepare_research_data()`, `build_historical_enhanced_features()`, `prepare_match_feature_store()`. So you usually run a single high-level module and it pulls what it needs. The canonical order when building from scratch:

```
src.data_pipeline        # download history -> matches/teams/ratings + Elo features (src.elo)
src.world_cup_identity   # 48-team identity layer (rankings, squads, confederations)
src.feature_store        # 2026 match feature store
src.enhanced_model       # logistic win-prob model + 2026 predictions
src.scoreline_model      # Poisson/Dixon-Coles exact-score probabilities
src.postgres_sync        # (optional) load everything into Postgres
```

Models are trained chronologically (`chronological_split` / train only on matches before each World Cup) to avoid leakage. The enhanced model applies upset/confederation protection (`probability_calibration.py`, `confederation_features.py`). The scoreline model layers lineup, group-opener tempo, and market-odds-anchor corrections on top of the Poisson matrix.

## Two storage paths — know which one you're touching

- **Files (`data/processed/*.parquet`, `data/features/*.parquet`, `reports/*.csv|*.json`)** — the source of truth for the dashboard. `api/data_store.py` loads these directly at startup (`DashboardDataStore.load()`).
- **Postgres** (`src.postgres_sync` + `src.postgres_views`) — a separate analytical store for the `postgres_queries` and `research_report` CLIs. The API does **not** read from it.

This means: if the dashboard shows stale or empty data, the fix is regenerating the relevant `reports/`/`data/` file, not touching Postgres.

**`src/project_paths.py` is the single source of truth for every input/output path.** Add or change file locations there, never hard-code paths in modules. (One exception currently lives in `api/data_store.py`: `GROUP_ADVANCE_PATH`.)

## Conventions

- All `src/` and `api/` modules start with `from __future__ import annotations` and use modern typing (`X | None`, `list[...]`). Match this.
- Team names are normalized through `src/team_names.py` (`normalize_team_name`); Chinese display names come from `api/team_locale.py` / `lineups_pipeline.TEAM_NAME_ZH`. Always normalize before joining on team name.
- DuckDB table DDL lives in `src/schema.py` (`SCHEMA_SQL`); the file-based DuckDB DB is `data/processed/fifa_research.duckdb`.
- Pydantic response models are in `api/schemas.py`; the matching TypeScript types are hand-mirrored in `web/src/types/api.ts` — keep them in sync when changing API shapes.
- `web/` uses the `@/` alias for `web/src/`. Pages are routed in `web/src/router/index.ts`; the single API client is `web/src/services/api.ts`.

## Domain / compliance constraint

The simulator (`/api/simulator/settle`, `web` SimulatorPage) is **probability research and virtual simulation only** — no real ordering, payment, or account features. This is an explicit product constraint (see the `compliance_note` in `api/data_store.py` metadata). Keep simulator/value-bet work framed as analysis, not gambling facilitation.

## Docker

`docker compose up --build` runs JupyterLab (`:8888`) and Postgres 16 (`:5432`); it does **not** run the API or web dashboard. Config comes from `.env` (copy from `.env.example`).
