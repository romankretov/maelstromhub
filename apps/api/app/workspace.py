from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssetORM,
    BacktestRunORM,
    CandleORM,
    DatasetORM,
    IngestionJobORM,
    StrategyORM,
    StrategyVersionORM,
    TimeframeORM,
)
from app.db.backtest_repositories import create_backtest_run
from app.db.repositories import _new_id, create_audit_event
from app.db.research_repositories import (
    SYSTEM_TIMEFRAME_INTERVALS,
    enqueue_dataset_candle_backfill,
    enqueue_dataset_feature_compute,
    ensure_system_timeframes,
    get_feature_summary,
    run_feature_ingestion_job,
)
from app.db.strategy_repositories import (
    _evaluate_backtest_run,
    create_strategy_version,
    list_strategy_templates,
    run_strategy_version_signals,
)
from app.market_intelligence import RegimeService
from maelstromhub_core import (
    Asset,
    BacktestRun,
    BacktestRunCreate,
    Candle,
    CandleBackfillRequest,
    Dataset,
    FeatureComputeRequest,
    IngestionJobStatus,
    StrategyStatus,
    StrategyVersionCreate,
    WorkspaceBacktestResult,
    WorkspaceCandleSummary,
    WorkspaceDataHealth,
    WorkspaceLoadMarketRequest,
    WorkspaceMarketMetadata,
    WorkspaceRange,
    WorkspaceRunBacktestRequest,
    WorkspaceState,
)

RANGE_DAYS = {
    WorkspaceRange.DAYS_7: 7,
    WorkspaceRange.DAYS_30: 30,
    WorkspaceRange.DAYS_90: 90,
    WorkspaceRange.DAYS_180: 180,
    WorkspaceRange.YEAR_1: 365,
}


class WorkspaceService:
    def __init__(self, regime_service: RegimeService | None = None) -> None:
        self.regime_service = regime_service or RegimeService()

    async def load_market(self, session: AsyncSession, payload: WorkspaceLoadMarketRequest) -> WorkspaceState:
        symbol = _normalize_symbol(payload.symbol)
        asset, timeframe, dataset = await self._resolve_market_dataset(
            session,
            symbol=symbol,
            timeframe=payload.timeframe,
            create_missing=True,
        )
        assert dataset is not None

        await enqueue_dataset_candle_backfill(
            session,
            dataset.id,
            CandleBackfillRequest(
                start_time=_range_start(payload.range),
                end_time=datetime.now(UTC),
            ),
        )

        candle_summary = await self._candle_summary(session, dataset.id)
        if candle_summary.total_candles > 0:
            feature_job = await enqueue_dataset_feature_compute(session, dataset.id, FeatureComputeRequest())
            await run_feature_ingestion_job(session, feature_job.id)

        feature_summary = await get_feature_summary(session, dataset.id)
        if feature_summary.total_snapshots > 0:
            await self.regime_service.compute_regimes(session, dataset.id)

        return await self.state(
            session,
            symbol=symbol,
            timeframe=timeframe.interval,
            range_value=payload.range,
        )

    async def state(
        self,
        session: AsyncSession,
        *,
        symbol: str,
        timeframe: str,
        range_value: WorkspaceRange,
    ) -> WorkspaceState:
        normalized_symbol = _normalize_symbol(symbol)
        asset, timeframe_orm, dataset = await self._resolve_market_dataset(
            session,
            symbol=normalized_symbol,
            timeframe=timeframe,
            create_missing=False,
        )
        templates = await list_strategy_templates(session)
        if dataset is None:
            return WorkspaceState(
                market=WorkspaceMarketMetadata(
                    symbol=normalized_symbol,
                    timeframe=timeframe_orm.interval,
                    range=range_value,
                    asset_id=asset.id if asset is not None else None,
                ),
                candle_summary=WorkspaceCandleSummary(),
                feature_summary=None,
                current_regime=None,
                available_strategy_templates=templates,
                latest_backtests=[],
                data_health=WorkspaceDataHealth(
                    status="missing",
                    detail="No market data container exists yet. Load the market to create it.",
                ),
            )

        candle_summary = await self._candle_summary(session, dataset.id)
        feature_summary = await get_feature_summary(session, dataset.id)
        if candle_summary.total_candles > 0 and feature_summary.total_snapshots == 0:
            feature_job = await enqueue_dataset_feature_compute(session, dataset.id, FeatureComputeRequest())
            await run_feature_ingestion_job(session, feature_job.id)
            feature_summary = await get_feature_summary(session, dataset.id)

        current_regime = await self.regime_service.current_regime(session, dataset.id)
        if feature_summary.total_snapshots > 0 and current_regime is None:
            await self.regime_service.compute_regimes(session, dataset.id)
            current_regime = await self.regime_service.current_regime(session, dataset.id)

        return WorkspaceState(
            market=WorkspaceMarketMetadata(
                symbol=normalized_symbol,
                timeframe=timeframe_orm.interval,
                range=range_value,
                asset_id=asset.id if asset is not None else None,
            ),
            dataset_id=dataset.id,
            candle_summary=candle_summary,
            latest_candles=await self._latest_candles(session, dataset.id),
            feature_summary=feature_summary,
            current_regime=current_regime,
            available_strategy_templates=templates,
            latest_backtests=await self._latest_backtests(session, dataset.id),
            data_health=await self._data_health(session, dataset, candle_summary),
        )

    async def run_backtest(
        self,
        session: AsyncSession,
        payload: WorkspaceRunBacktestRequest,
    ) -> WorkspaceBacktestResult:
        symbol = _normalize_symbol(payload.symbol)
        _, timeframe, dataset = await self._resolve_market_dataset(
            session,
            symbol=symbol,
            timeframe=payload.timeframe,
            create_missing=True,
        )
        assert dataset is not None

        candle_summary = await self._candle_summary(session, dataset.id)
        if candle_summary.total_candles == 0:
            await enqueue_dataset_candle_backfill(
                session,
                dataset.id,
                CandleBackfillRequest(
                    start_time=_range_start(payload.range),
                    end_time=datetime.now(UTC),
                ),
            )
            raise HTTPException(
                status_code=409,
                detail="Candles are not loaded yet. Refresh data first, then run the backtest after ingestion completes.",
            )

        feature_summary = await get_feature_summary(session, dataset.id)
        if feature_summary.total_snapshots == 0:
            feature_job = await enqueue_dataset_feature_compute(session, dataset.id, FeatureComputeRequest())
            await run_feature_ingestion_job(session, feature_job.id)
            feature_summary = await get_feature_summary(session, dataset.id)
        if feature_summary.total_snapshots == 0:
            raise HTTPException(
                status_code=409,
                detail="Feature snapshots are not available yet, so this strategy cannot be evaluated.",
            )

        current_regime = await self.regime_service.current_regime(session, dataset.id)
        if current_regime is None:
            await self.regime_service.compute_regimes(session, dataset.id)

        strategy = await self._get_or_create_workspace_strategy(
            session,
            symbol=symbol,
            timeframe=timeframe.interval,
            template_id=payload.template_id,
        )
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(
                template_id=payload.template_id,
                dataset_id=dataset.id,
                parameters=payload.parameters,
                allowed_regimes=payload.allowed_regimes,
            ),
        )
        signals = await run_strategy_version_signals(session, version.id)
        backtest = await create_backtest_run(
            session,
            version.id,
            BacktestRunCreate(
                starting_balance=payload.starting_balance,
                fee_bps=payload.fee_bps,
                slippage_bps=payload.slippage_bps,
            ),
        )
        run_orm = await session.get(BacktestRunORM, backtest.id)
        if run_orm is None:
            raise HTTPException(status_code=500, detail="Backtest completed but the run record could not be loaded.")

        return WorkspaceBacktestResult(
            workspace_state=await self.state(
                session,
                symbol=symbol,
                timeframe=timeframe.interval,
                range_value=payload.range,
            ),
            backtest=backtest,
            evaluation=_evaluate_backtest_run(run_orm),
            signals_written=signals.signals_written,
            total_signals=signals.total_signals,
        )

    async def _resolve_market_dataset(
        self,
        session: AsyncSession,
        *,
        symbol: str,
        timeframe: str,
        create_missing: bool,
    ) -> tuple[Asset | None, TimeframeORM, Dataset | None]:
        await ensure_system_timeframes(session)
        if timeframe not in SYSTEM_TIMEFRAME_INTERVALS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported system timeframe '{timeframe}'. Supported values: {', '.join(SYSTEM_TIMEFRAME_INTERVALS)}.",
            )
        timeframe_result = await session.execute(select(TimeframeORM).where(TimeframeORM.interval == timeframe))
        timeframe_orm = timeframe_result.scalar_one()

        asset_result = await session.execute(
            select(AssetORM)
            .where(func.upper(AssetORM.symbol) == symbol, AssetORM.venue == "hyperliquid")
            .order_by(AssetORM.created_at.asc())
            .limit(1)
        )
        asset_orm = asset_result.scalar_one_or_none()
        if asset_orm is None and create_missing:
            asset_orm = AssetORM(
                id=_new_id(),
                symbol=symbol,
                venue="hyperliquid",
                description=f"Workspace market for {symbol}.",
            )
            session.add(asset_orm)
            await session.flush()
            await create_audit_event(session, actor="system", action="created_asset", subject=asset_orm.id, flush=False)
            await session.commit()
            await session.refresh(asset_orm)

        asset = Asset.model_validate(asset_orm) if asset_orm is not None else None
        if asset_orm is None:
            return None, timeframe_orm, None

        dataset_result = await session.execute(
            select(DatasetORM)
            .where(
                DatasetORM.asset_id == asset_orm.id,
                DatasetORM.timeframe_id == timeframe_orm.id,
            )
            .order_by(DatasetORM.created_at.asc())
            .limit(1)
        )
        dataset_orm = dataset_result.scalar_one_or_none()
        if dataset_orm is None and create_missing:
            dataset_orm = DatasetORM(
                id=_new_id(),
                asset_id=asset_orm.id,
                timeframe_id=timeframe_orm.id,
                name=f"{symbol} {timeframe} market data",
                description="Created automatically by the workspace market loader.",
            )
            session.add(dataset_orm)
            await session.flush()
            await create_audit_event(
                session,
                actor="system",
                action="created_dataset",
                subject=dataset_orm.id,
                flush=False,
            )
            await session.commit()
            await session.refresh(dataset_orm)

        return asset, timeframe_orm, Dataset.model_validate(dataset_orm) if dataset_orm is not None else None

    async def _candle_summary(self, session: AsyncSession, dataset_id: UUID) -> WorkspaceCandleSummary:
        result = await session.execute(
            select(
                func.count(CandleORM.id),
                func.min(CandleORM.opened_at),
                func.max(CandleORM.opened_at),
            ).where(CandleORM.dataset_id == dataset_id)
        )
        count, first_timestamp, latest_timestamp = result.one()
        return WorkspaceCandleSummary(
            total_candles=int(count or 0),
            first_candle_timestamp=first_timestamp,
            latest_candle_timestamp=latest_timestamp,
        )

    async def _latest_candles(self, session: AsyncSession, dataset_id: UUID) -> list[Candle]:
        result = await session.execute(
            select(CandleORM)
            .where(CandleORM.dataset_id == dataset_id)
            .order_by(CandleORM.opened_at.desc())
            .limit(200)
        )
        candles = list(result.scalars())
        candles.reverse()
        return [Candle.model_validate(candle) for candle in candles]

    async def _latest_backtests(self, session: AsyncSession, dataset_id: UUID) -> list[BacktestRun]:
        result = await session.execute(
            select(BacktestRunORM)
            .join(StrategyVersionORM, StrategyVersionORM.id == BacktestRunORM.strategy_version_id)
            .where(StrategyVersionORM.dataset_id == dataset_id)
            .order_by(BacktestRunORM.created_at.desc())
            .limit(10)
        )
        return [BacktestRun.model_validate(run) for run in result.scalars()]

    async def _get_or_create_workspace_strategy(
        self,
        session: AsyncSession,
        *,
        symbol: str,
        timeframe: str,
        template_id: UUID,
    ) -> StrategyORM:
        templates = await list_strategy_templates(session)
        template = next((item for item in templates if item.id == template_id), None)
        if template is None:
            raise HTTPException(status_code=404, detail="Strategy template not found")
        strategy_name = f"Workspace {symbol} {timeframe} {template.name}"
        result = await session.execute(
            select(StrategyORM)
            .where(StrategyORM.name == strategy_name)
            .order_by(StrategyORM.created_at.asc())
            .limit(1)
        )
        strategy = result.scalar_one_or_none()
        if strategy is not None:
            return strategy

        strategy = StrategyORM(
            id=_new_id(),
            name=strategy_name,
            status=StrategyStatus.DRAFT.value,
            description=f"Workspace-managed strategy for {symbol} {timeframe}.",
        )
        session.add(strategy)
        await session.flush()
        await create_audit_event(
            session,
            actor="system",
            action="created_workspace_strategy",
            subject=strategy.id,
            flush=False,
        )
        await session.commit()
        await session.refresh(strategy)
        return strategy

    async def _data_health(
        self,
        session: AsyncSession,
        dataset: Dataset,
        candle_summary: WorkspaceCandleSummary,
    ) -> WorkspaceDataHealth:
        queued_result = await session.execute(
            select(func.count(IngestionJobORM.id)).where(
                IngestionJobORM.dataset_id == dataset.id,
                IngestionJobORM.status == IngestionJobStatus.QUEUED.value,
            )
        )
        queued_jobs = int(queued_result.scalar_one() or 0)
        if dataset.last_ingestion_status == IngestionJobStatus.FAILED.value:
            return WorkspaceDataHealth(
                status="failed",
                detail=dataset.last_ingestion_error or "Latest data load failed.",
                last_ingestion_status=dataset.last_ingestion_status,
                queued_jobs=queued_jobs,
            )
        if queued_jobs:
            return WorkspaceDataHealth(
                status="queued",
                detail="Candle backfill is queued.",
                last_ingestion_status=dataset.last_ingestion_status,
                queued_jobs=queued_jobs,
            )
        if candle_summary.total_candles == 0:
            return WorkspaceDataHealth(
                status="missing",
                detail="No candles are loaded for this market and timeframe yet.",
                last_ingestion_status=dataset.last_ingestion_status,
                queued_jobs=queued_jobs,
            )
        return WorkspaceDataHealth(
            status="ready",
            detail="Candles are available for chart, stats, and strategy research.",
            last_ingestion_status=dataset.last_ingestion_status,
            queued_jobs=queued_jobs,
        )


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="symbol is required")
    return normalized


def _range_start(range_value: WorkspaceRange) -> datetime:
    return datetime.now(UTC) - timedelta(days=RANGE_DAYS[range_value])
