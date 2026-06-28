import asyncio

from sqlalchemy import select

from app.db.models import IdeaORM, StrategyORM
from app.db.research_repositories import ensure_system_timeframes
from app.db.repositories import create_idea, create_strategy
from app.db.session import async_session_factory
from maelstromhub_core import IdeaCreate, StrategyCreate


async def seed() -> None:
    async with async_session_factory() as session:
        await ensure_system_timeframes(session)

        existing = await session.scalar(select(IdeaORM.id).limit(1))
        if existing:
            return

        funding = await create_idea(
            session,
            IdeaCreate(
                title="Funding rate mean reversion",
                thesis="Track persistent funding dislocations before promoting to strategy design.",
            ),
            actor="seed",
        )
        await create_idea(
            session,
            IdeaCreate(
                title="Breakout follow-through filter",
                thesis="Explore whether high-volume breakouts sustain after volatility normalization.",
            ),
            actor="seed",
        )

        existing_strategy = await session.scalar(select(StrategyORM.id).limit(1))
        if existing_strategy:
            return

        await create_strategy(
            session,
            StrategyCreate(
                name="Funding Fade Prototype",
                source_idea_id=funding.id,
                description="Draft strategy shell linked to the funding-rate research idea.",
            ),
            actor="seed",
        )


if __name__ == "__main__":
    asyncio.run(seed())
