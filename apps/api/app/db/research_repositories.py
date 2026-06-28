from datetime import UTC, datetime
from typing import Any, NamedTuple, TypeVar
from uuid import UUID

from fastapi import HTTPException

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssetORM,
    CandleORM,
    DatasetORM,
    ExperimentORM,
    FeatureORM,
    FeatureSnapshotORM,
    IngestionJobORM,
    TimeframeORM,
)
from app.db.repositories import _new_id, create_audit_event
from app.features.calculators import CandleInput, calculate_features
from app.providers.candles import CandleProvider, ProviderCandle, default_backfill_window
from maelstromhub_core import (
    Asset,
    AssetCreate,
    AssetUpdate,
    Candle,
    CandleBackfillRequest,
    CandleBackfillResult,
    Dataset,
    DatasetCreate,
    DatasetUpdate,
    Experiment,
    ExperimentCreate,
    ExperimentStatus,
    ExperimentUpdate,
    Feature,
    FeatureCreate,
    FeatureComputeRequest,
    FeatureSnapshot,
    FeatureSummary,
    FeatureSummaryItem,
    FeatureUpdate,
    IngestionJob,
    IngestionJobStatus,
    IngestionJobType,
    Timeframe,
    TimeframeCreate,
    TimeframeUpdate,
)

OrmModel = TypeVar("OrmModel")


class SystemTimeframe(NamedTuple):
    name: str
    interval: str
    description: str


SYSTEM_TIMEFRAMES: tuple[SystemTimeframe, ...] = (
    SystemTimeframe("1 minute", "1m", "System-supported exchange timeframe."),
    SystemTimeframe("5 minutes", "5m", "System-supported exchange timeframe."),
    SystemTimeframe("15 minutes", "15m", "System-supported exchange timeframe."),
    SystemTimeframe("1 hour", "1h", "System-supported exchange timeframe."),
    SystemTimeframe("4 hours", "4h", "System-supported exchange timeframe."),
    SystemTimeframe("1 day", "1d", "System-supported exchange timeframe."),
)
SYSTEM_TIMEFRAME_INTERVALS = tuple(timeframe.interval for timeframe in SYSTEM_TIMEFRAMES)
_SYSTEM_TIMEFRAME_ORDER = {interval: index for index, interval in enumerate(SYSTEM_TIMEFRAME_INTERVALS)}


async def _get_or_404(session: AsyncSession, model: type[OrmModel], item_id: UUID) -> OrmModel:
    item = await session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


def _apply_updates(item: object, values: dict[str, Any]) -> None:
    for key, value in values.items():
        setattr(item, key, value)


async def list_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(select(AssetORM).order_by(AssetORM.created_at.desc()))
    return [Asset.model_validate(asset) for asset in result.scalars()]


async def get_asset(session: AsyncSession, asset_id: UUID) -> Asset:
    return Asset.model_validate(await _get_or_404(session, AssetORM, asset_id))


async def create_asset(session: AsyncSession, payload: AssetCreate) -> Asset:
    asset = AssetORM(id=_new_id(), **payload.model_dump())
    session.add(asset)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_asset", subject=asset.id, flush=False)
    await session.commit()
    await session.refresh(asset)
    return Asset.model_validate(asset)


async def update_asset(session: AsyncSession, asset_id: UUID, payload: AssetUpdate) -> Asset:
    asset = await _get_or_404(session, AssetORM, asset_id)
    _apply_updates(asset, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(asset)
    return Asset.model_validate(asset)


async def delete_asset(session: AsyncSession, asset_id: UUID) -> None:
    asset = await _get_or_404(session, AssetORM, asset_id)
    await session.delete(asset)
    await session.commit()


async def list_timeframes(session: AsyncSession) -> list[Timeframe]:
    await ensure_system_timeframes(session)
    return await _list_timeframes(session)


async def _list_timeframes(session: AsyncSession) -> list[Timeframe]:
    result = await session.execute(select(TimeframeORM))
    timeframes = sorted(
        result.scalars(),
        key=lambda timeframe: (
            _SYSTEM_TIMEFRAME_ORDER.get(timeframe.interval, len(_SYSTEM_TIMEFRAME_ORDER)),
            timeframe.created_at,
        ),
    )
    return [Timeframe.model_validate(timeframe) for timeframe in timeframes]


async def ensure_system_timeframes(session: AsyncSession) -> list[Timeframe]:
    result = await session.execute(
        select(TimeframeORM).where(TimeframeORM.interval.in_(SYSTEM_TIMEFRAME_INTERVALS))
    )
    existing_by_interval = {timeframe.interval: timeframe for timeframe in result.scalars()}
    changed = False

    for definition in SYSTEM_TIMEFRAMES:
        timeframe = existing_by_interval.get(definition.interval)
        if timeframe is None:
            session.add(
                TimeframeORM(
                    id=_new_id(),
                    name=definition.name,
                    interval=definition.interval,
                    description=definition.description,
                )
            )
            changed = True
            continue

        if timeframe.name != definition.name or timeframe.description != definition.description:
            timeframe.name = definition.name
            timeframe.description = definition.description
            changed = True

    if changed:
        await session.flush()
        await session.commit()

    return await _list_timeframes(session)


async def get_timeframe(session: AsyncSession, timeframe_id: UUID) -> Timeframe:
    return Timeframe.model_validate(await _get_or_404(session, TimeframeORM, timeframe_id))


async def create_timeframe(session: AsyncSession, payload: TimeframeCreate) -> Timeframe:
    timeframe = TimeframeORM(id=_new_id(), **payload.model_dump())
    session.add(timeframe)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_timeframe", subject=timeframe.id, flush=False)
    await session.commit()
    await session.refresh(timeframe)
    return Timeframe.model_validate(timeframe)


async def update_timeframe(session: AsyncSession, timeframe_id: UUID, payload: TimeframeUpdate) -> Timeframe:
    timeframe = await _get_or_404(session, TimeframeORM, timeframe_id)
    _apply_updates(timeframe, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(timeframe)
    return Timeframe.model_validate(timeframe)


async def delete_timeframe(session: AsyncSession, timeframe_id: UUID) -> None:
    timeframe = await _get_or_404(session, TimeframeORM, timeframe_id)
    await session.delete(timeframe)
    await session.commit()


async def list_datasets(session: AsyncSession) -> list[Dataset]:
    result = await session.execute(select(DatasetORM).order_by(DatasetORM.created_at.desc()))
    return [Dataset.model_validate(dataset) for dataset in result.scalars()]


async def get_dataset(session: AsyncSession, dataset_id: UUID) -> Dataset:
    return Dataset.model_validate(await _get_or_404(session, DatasetORM, dataset_id))


async def create_dataset(session: AsyncSession, payload: DatasetCreate) -> Dataset:
    await ensure_system_timeframes(session)
    dataset = DatasetORM(id=_new_id(), **payload.model_dump())
    session.add(dataset)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_dataset", subject=dataset.id, flush=False)
    await session.commit()
    await session.refresh(dataset)
    return Dataset.model_validate(dataset)


async def update_dataset(session: AsyncSession, dataset_id: UUID, payload: DatasetUpdate) -> Dataset:
    dataset = await _get_or_404(session, DatasetORM, dataset_id)
    _apply_updates(dataset, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(dataset)
    return Dataset.model_validate(dataset)


async def delete_dataset(session: AsyncSession, dataset_id: UUID) -> None:
    dataset = await _get_or_404(session, DatasetORM, dataset_id)
    await session.delete(dataset)
    await session.commit()


async def list_dataset_candles(session: AsyncSession, dataset_id: UUID) -> list[Candle]:
    await _get_or_404(session, DatasetORM, dataset_id)
    result = await session.execute(
        select(CandleORM)
        .where(CandleORM.dataset_id == dataset_id)
        .order_by(CandleORM.opened_at.asc())
    )
    return [Candle.model_validate(candle) for candle in result.scalars()]


async def backfill_dataset_candles(
    session: AsyncSession,
    dataset_id: UUID,
    payload: CandleBackfillRequest,
    provider: CandleProvider,
) -> CandleBackfillResult:
    dataset = await _get_or_404(session, DatasetORM, dataset_id)
    asset = await _get_or_404(session, AssetORM, dataset.asset_id)
    timeframe = await _get_or_404(session, TimeframeORM, dataset.timeframe_id)
    start_time, end_time = _resolve_backfill_window(payload)

    try:
        provider_candles = await provider.get_historical_candles(
            symbol=asset.symbol,
            interval=timeframe.interval,
            start_time=start_time,
            end_time=end_time,
        )
        inserted, updated = await _upsert_candles(session, dataset.id, provider_candles)
        await _refresh_dataset_candle_stats(session, dataset)
        dataset.last_ingestion_status = "success"
        dataset.last_ingestion_error = None
        await create_audit_event(
            session,
            actor="system",
            action="backfilled_candles",
            subject=dataset.id,
            flush=False,
        )
        await session.commit()
        await session.refresh(dataset)
        return CandleBackfillResult(
            dataset_id=dataset.id,
            inserted=inserted,
            updated=updated,
            total_candles=dataset.candle_count,
            latest_candle_timestamp=dataset.latest_candle_timestamp,
            status="success",
        )
    except Exception as error:
        dataset.last_ingestion_status = "failed"
        dataset.last_ingestion_error = str(error)
        await session.commit()
        raise


async def enqueue_dataset_candle_backfill(
    session: AsyncSession,
    dataset_id: UUID,
    payload: CandleBackfillRequest,
) -> IngestionJob:
    await _get_or_404(session, DatasetORM, dataset_id)
    requested_start, requested_end = _resolve_backfill_window(payload)
    job = IngestionJobORM(
        id=_new_id(),
        dataset_id=dataset_id,
        job_type=IngestionJobType.CANDLE_BACKFILL.value,
        status=IngestionJobStatus.QUEUED.value,
        requested_start=requested_start,
        requested_end=requested_end,
    )
    session.add(job)
    await session.flush()
    await create_audit_event(
        session,
        actor="system",
        action="queued_ingestion_job",
        subject=job.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(job)
    return IngestionJob.model_validate(job)


async def get_ingestion_job(session: AsyncSession, job_id: UUID) -> IngestionJob:
    return IngestionJob.model_validate(await _get_or_404(session, IngestionJobORM, job_id))


async def list_dataset_ingestion_jobs(session: AsyncSession, dataset_id: UUID) -> list[IngestionJob]:
    await _get_or_404(session, DatasetORM, dataset_id)
    result = await session.execute(
        select(IngestionJobORM)
        .where(IngestionJobORM.dataset_id == dataset_id)
        .order_by(IngestionJobORM.created_at.desc())
    )
    return [IngestionJob.model_validate(job) for job in result.scalars()]


async def run_next_queued_ingestion_job(
    session: AsyncSession,
    provider: CandleProvider,
) -> IngestionJob | None:
    result = await session.execute(
        select(IngestionJobORM)
        .where(IngestionJobORM.status == IngestionJobStatus.QUEUED.value)
        .order_by(IngestionJobORM.created_at.asc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None
    return await run_ingestion_job(session, job.id, provider)


async def run_ingestion_job(
    session: AsyncSession,
    job_id: UUID,
    provider: CandleProvider,
) -> IngestionJob:
    job = await _get_or_404(session, IngestionJobORM, job_id)
    if job.job_type == IngestionJobType.FEATURE_COMPUTE.value:
        return await run_feature_ingestion_job(session, job_id)
    return await run_candle_ingestion_job(session, job_id, provider)


async def run_candle_ingestion_job(
    session: AsyncSession,
    job_id: UUID,
    provider: CandleProvider,
) -> IngestionJob:
    job = await _get_or_404(session, IngestionJobORM, job_id)
    dataset = await _get_or_404(session, DatasetORM, job.dataset_id)
    asset = await _get_or_404(session, AssetORM, dataset.asset_id)
    timeframe = await _get_or_404(session, TimeframeORM, dataset.timeframe_id)

    job.status = IngestionJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    dataset.last_ingestion_status = IngestionJobStatus.RUNNING.value
    dataset.last_ingestion_error = None
    await session.commit()

    try:
        provider_candles = await provider.get_historical_candles(
            symbol=asset.symbol,
            interval=timeframe.interval,
            start_time=job.requested_start,
            end_time=job.requested_end,
        )
        inserted, updated = await _upsert_candles(session, dataset.id, provider_candles)
        await _refresh_dataset_candle_stats(session, dataset)
        job.status = IngestionJobStatus.SUCCEEDED.value
        job.finished_at = datetime.now(UTC)
        job.candles_written = inserted + updated
        job.error_message = None
        dataset.last_ingestion_status = IngestionJobStatus.SUCCEEDED.value
        dataset.last_ingestion_error = None
        await create_audit_event(
            session,
            actor="system",
            action="succeeded_ingestion_job",
            subject=job.id,
            flush=False,
        )
        await session.commit()
    except Exception as error:
        job.status = IngestionJobStatus.FAILED.value
        job.finished_at = datetime.now(UTC)
        job.error_message = str(error)
        dataset.last_ingestion_status = IngestionJobStatus.FAILED.value
        dataset.last_ingestion_error = str(error)
        await create_audit_event(
            session,
            actor="system",
            action="failed_ingestion_job",
            subject=job.id,
            flush=False,
        )
        await session.commit()

    await session.refresh(job)
    return IngestionJob.model_validate(job)


async def enqueue_dataset_feature_compute(
    session: AsyncSession,
    dataset_id: UUID,
    payload: FeatureComputeRequest,
) -> IngestionJob:
    await _get_or_404(session, DatasetORM, dataset_id)
    job = IngestionJobORM(
        id=_new_id(),
        dataset_id=dataset_id,
        job_type=IngestionJobType.FEATURE_COMPUTE.value,
        status=IngestionJobStatus.QUEUED.value,
    )
    session.add(job)
    await session.flush()
    await create_audit_event(
        session,
        actor="system",
        action="queued_feature_job",
        subject=job.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(job)
    return IngestionJob.model_validate(job)


async def run_feature_ingestion_job(session: AsyncSession, job_id: UUID) -> IngestionJob:
    job = await _get_or_404(session, IngestionJobORM, job_id)
    dataset = await _get_or_404(session, DatasetORM, job.dataset_id)

    job.status = IngestionJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    job.error_message = None
    await session.commit()

    try:
        candles = await _load_feature_candles(session, dataset.id)
        feature_values = calculate_features(candles)
        inserted, updated = await _upsert_feature_snapshots(session, dataset.id, feature_values)
        job.status = IngestionJobStatus.SUCCEEDED.value
        job.finished_at = datetime.now(UTC)
        job.feature_snapshots_written = inserted + updated
        job.error_message = None
        await create_audit_event(
            session,
            actor="system",
            action="succeeded_feature_job",
            subject=job.id,
            flush=False,
        )
        await session.commit()
    except Exception as error:
        job.status = IngestionJobStatus.FAILED.value
        job.finished_at = datetime.now(UTC)
        job.error_message = str(error)
        await create_audit_event(
            session,
            actor="system",
            action="failed_feature_job",
            subject=job.id,
            flush=False,
        )
        await session.commit()

    await session.refresh(job)
    return IngestionJob.model_validate(job)


async def list_feature_snapshots(session: AsyncSession, dataset_id: UUID) -> list[FeatureSnapshot]:
    await _get_or_404(session, DatasetORM, dataset_id)
    result = await session.execute(
        select(FeatureSnapshotORM)
        .where(FeatureSnapshotORM.dataset_id == dataset_id)
        .order_by(FeatureSnapshotORM.timestamp.asc(), FeatureSnapshotORM.feature_name.asc())
    )
    return [_feature_snapshot_to_schema(snapshot) for snapshot in result.scalars()]


async def get_feature_summary(session: AsyncSession, dataset_id: UUID) -> FeatureSummary:
    snapshots = await list_feature_snapshots(session, dataset_id)
    grouped: dict[str, list[FeatureSnapshot]] = {}
    latest_timestamp = None
    for snapshot in snapshots:
        grouped.setdefault(snapshot.feature_name, []).append(snapshot)
        if latest_timestamp is None or snapshot.timestamp > latest_timestamp:
            latest_timestamp = snapshot.timestamp

    items: list[FeatureSummaryItem] = []
    for feature_name, feature_snapshots in sorted(grouped.items()):
        latest = max(feature_snapshots, key=lambda snapshot: snapshot.timestamp)
        items.append(
            FeatureSummaryItem(
                feature_name=feature_name,
                snapshot_count=len(feature_snapshots),
                latest_timestamp=latest.timestamp,
                latest_value=latest.numeric_value,
            )
        )

    return FeatureSummary(
        dataset_id=dataset_id,
        total_snapshots=len(snapshots),
        latest_timestamp=latest_timestamp,
        features=items,
    )


def _resolve_backfill_window(payload: CandleBackfillRequest):
    if payload.start_time and payload.end_time:
        return payload.start_time, payload.end_time
    default_start, default_end = default_backfill_window()
    return payload.start_time or default_start, payload.end_time or default_end


async def _upsert_candles(
    session: AsyncSession,
    dataset_id: UUID,
    provider_candles: list[ProviderCandle],
) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for provider_candle in provider_candles:
        opened_at = provider_candle.opened_at.astimezone(UTC)
        existing_result = await session.execute(
            select(CandleORM).where(
                CandleORM.dataset_id == dataset_id,
                CandleORM.opened_at == opened_at,
            )
        )
        existing = existing_result.scalar_one_or_none()
        values = {
            "open": provider_candle.open,
            "high": provider_candle.high,
            "low": provider_candle.low,
            "close": provider_candle.close,
            "volume": provider_candle.volume,
            "trade_count": provider_candle.trade_count,
        }
        if existing is None:
            session.add(
                CandleORM(
                    id=_new_id(),
                    dataset_id=dataset_id,
                    opened_at=opened_at,
                    **values,
                )
            )
            inserted += 1
        else:
            _apply_updates(existing, values)
            updated += 1
    await session.flush()
    return inserted, updated


async def _refresh_dataset_candle_stats(session: AsyncSession, dataset: DatasetORM) -> None:
    count_result = await session.execute(select(func.count()).select_from(CandleORM).where(CandleORM.dataset_id == dataset.id))
    latest_result = await session.execute(select(func.max(CandleORM.opened_at)).where(CandleORM.dataset_id == dataset.id))
    dataset.candle_count = int(count_result.scalar_one() or 0)
    dataset.latest_candle_timestamp = latest_result.scalar_one_or_none()


async def _load_feature_candles(session: AsyncSession, dataset_id: UUID) -> list[CandleInput]:
    result = await session.execute(
        select(CandleORM)
        .where(CandleORM.dataset_id == dataset_id)
        .order_by(CandleORM.opened_at.asc())
    )
    return [
        CandleInput(
            timestamp=candle.opened_at,
            open=float(candle.open),
            high=float(candle.high),
            low=float(candle.low),
            close=float(candle.close),
        )
        for candle in result.scalars()
    ]


async def _upsert_feature_snapshots(session: AsyncSession, dataset_id: UUID, feature_values) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for value in feature_values:
        timestamp = value.timestamp.astimezone(UTC)
        existing_result = await session.execute(
            select(FeatureSnapshotORM).where(
                FeatureSnapshotORM.dataset_id == dataset_id,
                FeatureSnapshotORM.timestamp == timestamp,
                FeatureSnapshotORM.feature_name == value.feature_name,
            )
        )
        existing = existing_result.scalar_one_or_none()
        values = {
            "numeric_value": value.numeric_value,
            "metadata_json": value.metadata,
        }
        if existing is None:
            session.add(
                FeatureSnapshotORM(
                    id=_new_id(),
                    dataset_id=dataset_id,
                    timestamp=timestamp,
                    feature_name=value.feature_name,
                    **values,
                )
            )
            inserted += 1
        else:
            _apply_updates(existing, values)
            updated += 1
    await session.flush()
    return inserted, updated


def _feature_snapshot_to_schema(snapshot: FeatureSnapshotORM) -> FeatureSnapshot:
    return FeatureSnapshot(
        id=snapshot.id,
        dataset_id=snapshot.dataset_id,
        timestamp=snapshot.timestamp,
        feature_name=snapshot.feature_name,
        numeric_value=float(snapshot.numeric_value),
        metadata=snapshot.metadata_json,
        created_at=snapshot.created_at,
    )


async def list_features(session: AsyncSession) -> list[Feature]:
    result = await session.execute(select(FeatureORM).order_by(FeatureORM.created_at.desc()))
    return [Feature.model_validate(feature) for feature in result.scalars()]


async def get_feature(session: AsyncSession, feature_id: UUID) -> Feature:
    return Feature.model_validate(await _get_or_404(session, FeatureORM, feature_id))


async def create_feature(session: AsyncSession, payload: FeatureCreate) -> Feature:
    feature = FeatureORM(id=_new_id(), **payload.model_dump())
    session.add(feature)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_feature", subject=feature.id, flush=False)
    await session.commit()
    await session.refresh(feature)
    return Feature.model_validate(feature)


async def update_feature(session: AsyncSession, feature_id: UUID, payload: FeatureUpdate) -> Feature:
    feature = await _get_or_404(session, FeatureORM, feature_id)
    _apply_updates(feature, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(feature)
    return Feature.model_validate(feature)


async def delete_feature(session: AsyncSession, feature_id: UUID) -> None:
    feature = await _get_or_404(session, FeatureORM, feature_id)
    await session.delete(feature)
    await session.commit()


async def list_experiments(session: AsyncSession) -> list[Experiment]:
    result = await session.execute(select(ExperimentORM).order_by(ExperimentORM.created_at.desc()))
    return [Experiment.model_validate(experiment) for experiment in result.scalars()]


async def get_experiment(session: AsyncSession, experiment_id: UUID) -> Experiment:
    return Experiment.model_validate(await _get_or_404(session, ExperimentORM, experiment_id))


async def create_experiment(session: AsyncSession, payload: ExperimentCreate) -> Experiment:
    experiment = ExperimentORM(
        id=_new_id(),
        status=ExperimentStatus.DRAFT.value,
        **payload.model_dump(),
    )
    session.add(experiment)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_experiment", subject=experiment.id, flush=False)
    await session.commit()
    await session.refresh(experiment)
    return Experiment.model_validate(experiment)


async def update_experiment(session: AsyncSession, experiment_id: UUID, payload: ExperimentUpdate) -> Experiment:
    experiment = await _get_or_404(session, ExperimentORM, experiment_id)
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value
    _apply_updates(experiment, updates)
    await session.commit()
    await session.refresh(experiment)
    return Experiment.model_validate(experiment)


async def delete_experiment(session: AsyncSession, experiment_id: UUID) -> None:
    experiment = await _get_or_404(session, ExperimentORM, experiment_id)
    await session.delete(experiment)
    await session.commit()
