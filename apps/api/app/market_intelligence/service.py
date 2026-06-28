from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import create_audit_event
from app.market_intelligence.engine import RegimeEngine
from app.market_intelligence.repository import RegimeRepository
from maelstromhub_core import MarketIntelligence, MarketRegimeSnapshot, RegimeComputationResult


class RegimeService:
    def __init__(self, repository: RegimeRepository | None = None, engine: RegimeEngine | None = None) -> None:
        self.repository = repository or RegimeRepository()
        self.engine = engine or RegimeEngine()

    async def compute_regimes(self, session: AsyncSession, dataset_id: str) -> RegimeComputationResult:
        await self.repository.ensure_dataset(session, dataset_id)
        await create_audit_event(
            session,
            actor="system",
            action="started_regime_computation",
            subject=dataset_id,
            flush=False,
        )
        await session.commit()
        try:
            snapshots = await self.repository.load_feature_snapshots(session, dataset_id)
            classifications = self.engine.compute(snapshots)
            written = await self.repository.upsert_classifications(session, dataset_id, classifications)
            current = await self.repository.current_snapshot(session, dataset_id)
            await create_audit_event(
                session,
                actor="system",
                action="completed_regime_computation",
                subject=dataset_id,
                flush=False,
            )
            await session.commit()
            return RegimeComputationResult(
                dataset_id=dataset_id,
                snapshots_written=written,
                current_regime=current,
            )
        except Exception:
            await create_audit_event(
                session,
                actor="system",
                action="failed_regime_computation",
                subject=dataset_id,
                flush=False,
            )
            await session.commit()
            raise

    async def list_snapshots(self, session: AsyncSession, dataset_id: str) -> list[MarketRegimeSnapshot]:
        return await self.repository.list_snapshots(session, dataset_id)

    async def current_regime(self, session: AsyncSession, dataset_id: str) -> MarketRegimeSnapshot | None:
        return await self.repository.current_snapshot(session, dataset_id)

    async def market_intelligence(self, session: AsyncSession, dataset_id: str) -> MarketIntelligence:
        return MarketIntelligence(dataset_id=dataset_id, regime=await self.current_regime(session, dataset_id))
