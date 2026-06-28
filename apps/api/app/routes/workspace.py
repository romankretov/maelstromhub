from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.workspace import WorkspaceService
from maelstromhub_core import (
    WorkspaceBacktestResult,
    WorkspaceLoadMarketRequest,
    WorkspaceRange,
    WorkspaceRunBacktestRequest,
    WorkspaceState,
)

router = APIRouter(prefix="/workspace")
workspace_service = WorkspaceService()

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("/load-market")
async def post_load_market(payload: WorkspaceLoadMarketRequest, session: SessionDependency) -> WorkspaceState:
    return await workspace_service.load_market(session, payload)


@router.post("/run-backtest")
async def post_run_backtest(
    payload: WorkspaceRunBacktestRequest,
    session: SessionDependency,
) -> WorkspaceBacktestResult:
    return await workspace_service.run_backtest(session, payload)


@router.get("/state")
async def get_workspace_state(
    session: SessionDependency,
    symbol: str,
    timeframe: str,
    range_value: WorkspaceRange = Query(alias="range"),
) -> WorkspaceState:
    return await workspace_service.state(
        session,
        symbol=symbol,
        timeframe=timeframe,
        range_value=range_value,
    )
