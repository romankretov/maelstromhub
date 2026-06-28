from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import (
    create_idea,
    create_strategy,
    list_audit_events,
    list_ideas,
    list_strategies,
)
from app.db.session import get_session
from maelstromhub_core import AuditEvent, Idea, IdeaCreate, Strategy, StrategyCreate

router = APIRouter()

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/ideas")
async def get_ideas(session: SessionDependency) -> dict[str, list[Idea]]:
    return {"ideas": await list_ideas(session)}


@router.post("/ideas", status_code=201)
async def post_idea(payload: IdeaCreate, session: SessionDependency) -> Idea:
    return await create_idea(session, payload)


@router.get("/strategies")
async def get_strategies(session: SessionDependency) -> dict[str, list[Strategy]]:
    return {"strategies": await list_strategies(session)}


@router.post("/strategies", status_code=201)
async def post_strategy(payload: StrategyCreate, session: SessionDependency) -> Strategy:
    return await create_strategy(session, payload)


@router.get("/audit-events")
async def get_audit_events(session: SessionDependency) -> dict[str, list[AuditEvent]]:
    return {"audit_events": await list_audit_events(session)}
