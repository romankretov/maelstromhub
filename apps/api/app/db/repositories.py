from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventORM, IdeaORM, StrategyORM
from maelstromhub_core import AuditEvent, Idea, IdeaCreate, Strategy, StrategyCreate, StrategyStatus


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


def idea_to_schema(idea: IdeaORM) -> Idea:
    return Idea.model_validate(idea)


def strategy_to_schema(strategy: StrategyORM) -> Strategy:
    return Strategy.model_validate(strategy)


def audit_event_to_schema(event: AuditEventORM) -> AuditEvent:
    return AuditEvent.model_validate(event)


async def list_ideas(session: AsyncSession) -> list[Idea]:
    result = await session.execute(select(IdeaORM).order_by(IdeaORM.created_at.desc()))
    return [idea_to_schema(idea) for idea in result.scalars()]


async def create_idea(session: AsyncSession, payload: IdeaCreate, actor: str = "system") -> Idea:
    idea = IdeaORM(id=_new_id("idea"), title=payload.title, thesis=payload.thesis)
    session.add(idea)
    await session.flush()
    await create_audit_event(
        session,
        actor=actor,
        action="created_idea",
        subject=idea.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(idea)
    return idea_to_schema(idea)


async def list_strategies(session: AsyncSession) -> list[Strategy]:
    result = await session.execute(select(StrategyORM).order_by(StrategyORM.created_at.desc()))
    return [strategy_to_schema(strategy) for strategy in result.scalars()]


async def create_strategy(session: AsyncSession, payload: StrategyCreate, actor: str = "system") -> Strategy:
    strategy = StrategyORM(
        id=_new_id("strategy"),
        name=payload.name,
        status=StrategyStatus.DRAFT.value,
        source_idea_id=payload.source_idea_id,
        description=payload.description,
    )
    session.add(strategy)
    await session.flush()
    await create_audit_event(
        session,
        actor=actor,
        action="created_strategy",
        subject=strategy.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(strategy)
    return strategy_to_schema(strategy)


async def list_audit_events(session: AsyncSession) -> list[AuditEvent]:
    result = await session.execute(select(AuditEventORM).order_by(AuditEventORM.created_at.desc()))
    return [audit_event_to_schema(event) for event in result.scalars()]


async def create_audit_event(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    subject: str,
    flush: bool = True,
) -> AuditEventORM:
    event = AuditEventORM(
        id=_new_id("audit"),
        actor=actor,
        action=action,
        subject=subject,
    )
    session.add(event)
    if flush:
        await session.flush()
    return event
