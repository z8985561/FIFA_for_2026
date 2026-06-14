from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .data_store import DashboardDataStore
from .schemas import (
    DataQualityRow,
    GroupAdvanceRow,
    HealthResponse,
    MatchDetail,
    MatchReviewRow,
    MatchSummary,
    MetadataResponse,
    ScheduleMatch,
    ScorelineRow,
    SimulatorRequest,
    SimulatorResponse,
    TeamCompareResponse,
    TeamProfileResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = DashboardDataStore.load()
    yield


app = FastAPI(
    title="FIFA 2026 Research Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_store() -> DashboardDataStore:
    return app.state.store


@app.get("/api/health", response_model=HealthResponse)
def health(store: Annotated[DashboardDataStore, Depends(get_store)]) -> HealthResponse:
    return HealthResponse(status="ok", row_counts=store.row_counts())


@app.get("/api/metadata", response_model=MetadataResponse)
def metadata(store: Annotated[DashboardDataStore, Depends(get_store)]) -> MetadataResponse:
    return store.metadata()


@app.get("/api/matches", response_model=list[MatchSummary])
def list_matches(
    store: Annotated[DashboardDataStore, Depends(get_store)],
    limit: Annotated[int | None, Query(ge=1, le=104)] = None,
    group_name: str | None = None,
) -> list[MatchSummary]:
    return store.list_matches(limit=limit, group_name=group_name)


@app.get("/api/schedule", response_model=list[ScheduleMatch])
def list_schedule(
    store: Annotated[DashboardDataStore, Depends(get_store)],
    stage: str | None = None,
    group_name: str | None = None,
) -> list[ScheduleMatch]:
    return store.list_schedule(stage=stage, group_name=group_name)


@app.get("/api/data-quality", response_model=list[DataQualityRow])
def list_data_quality(
    store: Annotated[DashboardDataStore, Depends(get_store)],
) -> list[DataQualityRow]:
    return store.list_data_quality()


@app.get("/api/matches/{match_no}", response_model=MatchDetail)
def get_match(
    match_no: int,
    store: Annotated[DashboardDataStore, Depends(get_store)],
) -> MatchDetail:
    try:
        return store.get_match(match_no)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/matches/{match_no}/scorelines", response_model=list[ScorelineRow])
def list_match_scorelines(
    match_no: int,
    store: Annotated[DashboardDataStore, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    sort_by: str = "rank",
) -> list[ScorelineRow]:
    return store.list_scorelines(match_no=match_no, limit=limit, sort_by=sort_by)


@app.get("/api/scorelines/value", response_model=list[ScorelineRow])
def list_value_scorelines(
    store: Annotated[DashboardDataStore, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    signal: str | None = None,
    sort_by: str = "edge",
) -> list[ScorelineRow]:
    return store.list_scorelines(limit=limit, signal=signal, sort_by=sort_by)


@app.get("/api/reviews/matches", response_model=list[MatchReviewRow])
def list_match_reviews(
    store: Annotated[DashboardDataStore, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    review_bucket: str | None = None,
) -> list[MatchReviewRow]:
    return store.list_match_reviews(limit=limit, review_bucket=review_bucket)


@app.get("/api/groups/advance", response_model=list[GroupAdvanceRow])
def list_group_advance(
    store: Annotated[DashboardDataStore, Depends(get_store)],
    group_name: str | None = None,
) -> list[GroupAdvanceRow]:
    return store.list_group_advance(group_name=group_name)

@app.get("/api/teams/compare", response_model=TeamCompareResponse)
def compare_teams(
    team_a: str,
    team_b: str,
    store: Annotated[DashboardDataStore, Depends(get_store)],
) -> TeamCompareResponse:
    return store.compare_teams(team_a, team_b)



@app.get("/api/elo/distribution")
def elo_distribution(
    store: Annotated[DashboardDataStore, Depends(get_store)],
) -> list[dict[str, object]]:
    return store.elo_distribution()


@app.get("/api/teams/{team_name}", response_model=TeamProfileResponse)
def team_profile(
    team_name: str,
    store: Annotated[DashboardDataStore, Depends(get_store)],
) -> TeamProfileResponse:
    return store.team_profile(team_name)


@app.post("/api/simulator/settle", response_model=SimulatorResponse)
def settle_simulator(
    request: SimulatorRequest,
    store: Annotated[DashboardDataStore, Depends(get_store)],
) -> SimulatorResponse:
    try:
        return store.settle_simulator(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
