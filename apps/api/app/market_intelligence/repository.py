from datetime import UTC
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DatasetORM, FeatureSnapshotORM, MarketRegimeSnapshotORM
from app.db.repositories import _new_id
from app.market_intelligence.classifier import RegimeClassification
from maelstromhub_core import (
    LiquidityRegime,
    MarketRegimeSnapshot,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)


class RegimeRepository:
    async def ensure_dataset(self, session: AsyncSession, dataset_id: str) -> None:
        if await session.get(DatasetORM, dataset_id) is None:
            raise HTTPException(status_code=404, detail="Resource not found")

    async def load_feature_snapshots(self, session: AsyncSession, dataset_id: str) -> list[tuple[Any, str, float]]:
        await self.ensure_dataset(session, dataset_id)
        result = await session.execute(
            select(FeatureSnapshotORM)
            .where(FeatureSnapshotORM.dataset_id == dataset_id)
            .order_by(FeatureSnapshotORM.timestamp.asc())
        )
        return [
            (snapshot.timestamp.astimezone(UTC), snapshot.feature_name, float(snapshot.numeric_value))
            for snapshot in result.scalars()
        ]

    async def upsert_classifications(
        self,
        session: AsyncSession,
        dataset_id: str,
        classifications: list[RegimeClassification],
    ) -> int:
        written = 0
        for classification in classifications:
            timestamp = classification.timestamp.astimezone(UTC)
            existing_result = await session.execute(
                select(MarketRegimeSnapshotORM).where(
                    MarketRegimeSnapshotORM.dataset_id == dataset_id,
                    MarketRegimeSnapshotORM.timestamp == timestamp,
                )
            )
            existing = existing_result.scalar_one_or_none()
            values = {
                "trend_regime": classification.trend_regime.value,
                "volatility_regime": classification.volatility_regime.value,
                "liquidity_regime": classification.liquidity_regime.value,
                "risk_regime": classification.risk_regime.value,
                "regime_label": classification.regime_label,
                "confidence": classification.confidence,
                "explanation": classification.explanation,
                "metadata_json": classification.metadata,
            }
            if existing is None:
                session.add(
                    MarketRegimeSnapshotORM(
                        id=_new_id("market-regime"),
                        dataset_id=dataset_id,
                        timestamp=timestamp,
                        **values,
                    )
                )
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
            written += 1
        await session.flush()
        return written

    async def list_snapshots(self, session: AsyncSession, dataset_id: str) -> list[MarketRegimeSnapshot]:
        await self.ensure_dataset(session, dataset_id)
        result = await session.execute(
            select(MarketRegimeSnapshotORM)
            .where(MarketRegimeSnapshotORM.dataset_id == dataset_id)
            .order_by(MarketRegimeSnapshotORM.timestamp.desc())
        )
        return [self.to_schema(snapshot) for snapshot in result.scalars()]

    async def current_snapshot(self, session: AsyncSession, dataset_id: str) -> MarketRegimeSnapshot | None:
        await self.ensure_dataset(session, dataset_id)
        result = await session.execute(
            select(MarketRegimeSnapshotORM)
            .where(MarketRegimeSnapshotORM.dataset_id == dataset_id)
            .order_by(MarketRegimeSnapshotORM.timestamp.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        return self.to_schema(snapshot) if snapshot is not None else None

    def to_schema(self, snapshot: MarketRegimeSnapshotORM) -> MarketRegimeSnapshot:
        return MarketRegimeSnapshot(
            id=snapshot.id,
            dataset_id=snapshot.dataset_id,
            timestamp=snapshot.timestamp,
            trend_regime=TrendRegime(snapshot.trend_regime),
            volatility_regime=VolatilityRegime(snapshot.volatility_regime),
            liquidity_regime=LiquidityRegime(snapshot.liquidity_regime),
            risk_regime=RiskRegime(snapshot.risk_regime),
            regime_label=snapshot.regime_label,
            confidence=float(snapshot.confidence),
            explanation=snapshot.explanation,
            metadata=snapshot.metadata_json,
            created_at=snapshot.created_at,
        )
