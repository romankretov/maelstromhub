from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssetORM, DatasetORM, ExperimentORM, FeatureORM, TimeframeORM
from app.db.repositories import _new_id, create_audit_event
from maelstromhub_core import (
    Asset,
    AssetCreate,
    AssetUpdate,
    Dataset,
    DatasetCreate,
    DatasetUpdate,
    Experiment,
    ExperimentCreate,
    ExperimentStatus,
    ExperimentUpdate,
    Feature,
    FeatureCreate,
    FeatureUpdate,
    Timeframe,
    TimeframeCreate,
    TimeframeUpdate,
)

OrmModel = TypeVar("OrmModel")


async def _get_or_404(session: AsyncSession, model: type[OrmModel], item_id: str) -> OrmModel:
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


async def get_asset(session: AsyncSession, asset_id: str) -> Asset:
    return Asset.model_validate(await _get_or_404(session, AssetORM, asset_id))


async def create_asset(session: AsyncSession, payload: AssetCreate) -> Asset:
    asset = AssetORM(id=_new_id("asset"), **payload.model_dump())
    session.add(asset)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_asset", subject=asset.id, flush=False)
    await session.commit()
    await session.refresh(asset)
    return Asset.model_validate(asset)


async def update_asset(session: AsyncSession, asset_id: str, payload: AssetUpdate) -> Asset:
    asset = await _get_or_404(session, AssetORM, asset_id)
    _apply_updates(asset, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(asset)
    return Asset.model_validate(asset)


async def delete_asset(session: AsyncSession, asset_id: str) -> None:
    asset = await _get_or_404(session, AssetORM, asset_id)
    await session.delete(asset)
    await session.commit()


async def list_timeframes(session: AsyncSession) -> list[Timeframe]:
    result = await session.execute(select(TimeframeORM).order_by(TimeframeORM.created_at.desc()))
    return [Timeframe.model_validate(timeframe) for timeframe in result.scalars()]


async def get_timeframe(session: AsyncSession, timeframe_id: str) -> Timeframe:
    return Timeframe.model_validate(await _get_or_404(session, TimeframeORM, timeframe_id))


async def create_timeframe(session: AsyncSession, payload: TimeframeCreate) -> Timeframe:
    timeframe = TimeframeORM(id=_new_id("timeframe"), **payload.model_dump())
    session.add(timeframe)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_timeframe", subject=timeframe.id, flush=False)
    await session.commit()
    await session.refresh(timeframe)
    return Timeframe.model_validate(timeframe)


async def update_timeframe(session: AsyncSession, timeframe_id: str, payload: TimeframeUpdate) -> Timeframe:
    timeframe = await _get_or_404(session, TimeframeORM, timeframe_id)
    _apply_updates(timeframe, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(timeframe)
    return Timeframe.model_validate(timeframe)


async def delete_timeframe(session: AsyncSession, timeframe_id: str) -> None:
    timeframe = await _get_or_404(session, TimeframeORM, timeframe_id)
    await session.delete(timeframe)
    await session.commit()


async def list_datasets(session: AsyncSession) -> list[Dataset]:
    result = await session.execute(select(DatasetORM).order_by(DatasetORM.created_at.desc()))
    return [Dataset.model_validate(dataset) for dataset in result.scalars()]


async def get_dataset(session: AsyncSession, dataset_id: str) -> Dataset:
    return Dataset.model_validate(await _get_or_404(session, DatasetORM, dataset_id))


async def create_dataset(session: AsyncSession, payload: DatasetCreate) -> Dataset:
    dataset = DatasetORM(id=_new_id("dataset"), **payload.model_dump())
    session.add(dataset)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_dataset", subject=dataset.id, flush=False)
    await session.commit()
    await session.refresh(dataset)
    return Dataset.model_validate(dataset)


async def update_dataset(session: AsyncSession, dataset_id: str, payload: DatasetUpdate) -> Dataset:
    dataset = await _get_or_404(session, DatasetORM, dataset_id)
    _apply_updates(dataset, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(dataset)
    return Dataset.model_validate(dataset)


async def delete_dataset(session: AsyncSession, dataset_id: str) -> None:
    dataset = await _get_or_404(session, DatasetORM, dataset_id)
    await session.delete(dataset)
    await session.commit()


async def list_features(session: AsyncSession) -> list[Feature]:
    result = await session.execute(select(FeatureORM).order_by(FeatureORM.created_at.desc()))
    return [Feature.model_validate(feature) for feature in result.scalars()]


async def get_feature(session: AsyncSession, feature_id: str) -> Feature:
    return Feature.model_validate(await _get_or_404(session, FeatureORM, feature_id))


async def create_feature(session: AsyncSession, payload: FeatureCreate) -> Feature:
    feature = FeatureORM(id=_new_id("feature"), **payload.model_dump())
    session.add(feature)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_feature", subject=feature.id, flush=False)
    await session.commit()
    await session.refresh(feature)
    return Feature.model_validate(feature)


async def update_feature(session: AsyncSession, feature_id: str, payload: FeatureUpdate) -> Feature:
    feature = await _get_or_404(session, FeatureORM, feature_id)
    _apply_updates(feature, payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(feature)
    return Feature.model_validate(feature)


async def delete_feature(session: AsyncSession, feature_id: str) -> None:
    feature = await _get_or_404(session, FeatureORM, feature_id)
    await session.delete(feature)
    await session.commit()


async def list_experiments(session: AsyncSession) -> list[Experiment]:
    result = await session.execute(select(ExperimentORM).order_by(ExperimentORM.created_at.desc()))
    return [Experiment.model_validate(experiment) for experiment in result.scalars()]


async def get_experiment(session: AsyncSession, experiment_id: str) -> Experiment:
    return Experiment.model_validate(await _get_or_404(session, ExperimentORM, experiment_id))


async def create_experiment(session: AsyncSession, payload: ExperimentCreate) -> Experiment:
    experiment = ExperimentORM(
        id=_new_id("experiment"),
        status=ExperimentStatus.DRAFT.value,
        **payload.model_dump(),
    )
    session.add(experiment)
    await session.flush()
    await create_audit_event(session, actor="system", action="created_experiment", subject=experiment.id, flush=False)
    await session.commit()
    await session.refresh(experiment)
    return Experiment.model_validate(experiment)


async def update_experiment(session: AsyncSession, experiment_id: str, payload: ExperimentUpdate) -> Experiment:
    experiment = await _get_or_404(session, ExperimentORM, experiment_id)
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value
    _apply_updates(experiment, updates)
    await session.commit()
    await session.refresh(experiment)
    return Experiment.model_validate(experiment)


async def delete_experiment(session: AsyncSession, experiment_id: str) -> None:
    experiment = await _get_or_404(session, ExperimentORM, experiment_id)
    await session.delete(experiment)
    await session.commit()
