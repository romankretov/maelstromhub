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
from app.db.strategy_repositories import (
    create_strategy_version,
    list_strategy_templates,
    list_strategy_version_signals,
    list_strategy_versions,
    run_strategy_version_signals,
)
from maelstromhub_core import (
    AuditEvent,
    Idea,
    IdeaCreate,
    Signal,
    SignalRunResult,
    Strategy,
    StrategyCreate,
    StrategyTemplate,
    StrategyVersion,
    StrategyVersionCreate,
)

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


@router.get("/strategy-templates")
async def get_strategy_templates(session: SessionDependency) -> dict[str, list[StrategyTemplate]]:
    return {"strategy_templates": await list_strategy_templates(session)}


@router.post("/strategies/{strategy_id}/versions", status_code=201)
async def post_strategy_version(
    strategy_id: str,
    payload: StrategyVersionCreate,
    session: SessionDependency,
) -> StrategyVersion:
    return await create_strategy_version(session, strategy_id, payload)


@router.get("/strategies/{strategy_id}/versions")
async def get_strategy_versions(strategy_id: str, session: SessionDependency) -> dict[str, list[StrategyVersion]]:
    return {"strategy_versions": await list_strategy_versions(session, strategy_id)}


@router.post("/strategy-versions/{version_id}/run-signals")
async def post_strategy_version_signals(version_id: str, session: SessionDependency) -> SignalRunResult:
    return await run_strategy_version_signals(session, version_id)


@router.get("/strategy-versions/{version_id}/signals")
async def get_strategy_version_signals(version_id: str, session: SessionDependency) -> dict[str, list[Signal]]:
    return {"signals": await list_strategy_version_signals(session, version_id)}


@router.get("/audit-events")
async def get_audit_events(session: SessionDependency) -> dict[str, list[AuditEvent]]:
    return {"audit_events": await list_audit_events(session)}
