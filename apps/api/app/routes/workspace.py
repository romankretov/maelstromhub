from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.workspace import WorkspaceService
from maelstromhub_core import (
    WorkspaceBacktestResult,
    WorkspaceLoadMarketRequest,
    WorkspaceNote,
    WorkspaceNoteCreate,
    WorkspaceNoteUpdate,
    WorkspaceRange,
    WorkspaceOptimisationResult,
    WorkspaceOptimiseRequest,
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


@router.post("/optimise")
async def post_optimise(
    payload: WorkspaceOptimiseRequest,
    session: SessionDependency,
) -> WorkspaceOptimisationResult:
    return await workspace_service.optimise(session, payload)


@router.get("/notes")
async def get_notes(
    session: SessionDependency,
    symbol: str,
    timeframe: str,
) -> dict[str, list[WorkspaceNote]]:
    return {"workspace_notes": await workspace_service.list_notes(session, symbol=symbol, timeframe=timeframe)}


@router.post("/notes", status_code=201)
async def post_note(payload: WorkspaceNoteCreate, session: SessionDependency) -> WorkspaceNote:
    return await workspace_service.create_note(session, payload)


@router.patch("/notes/{note_id}")
async def patch_note(note_id: UUID, payload: WorkspaceNoteUpdate, session: SessionDependency) -> WorkspaceNote:
    return await workspace_service.update_note(session, note_id, payload)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: UUID, session: SessionDependency) -> Response:
    await workspace_service.delete_note(session, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
