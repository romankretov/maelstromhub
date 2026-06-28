from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.research_repositories import (
    create_asset,
    create_dataset,
    create_experiment,
    create_feature,
    create_timeframe,
    delete_asset,
    delete_dataset,
    delete_experiment,
    delete_feature,
    delete_timeframe,
    get_asset,
    get_dataset,
    get_experiment,
    get_feature,
    get_ingestion_job,
    get_timeframe,
    enqueue_dataset_candle_backfill,
    list_dataset_candles,
    list_dataset_ingestion_jobs,
    list_assets,
    list_datasets,
    list_experiments,
    list_features,
    list_timeframes,
    update_asset,
    update_dataset,
    update_experiment,
    update_feature,
    update_timeframe,
)
from app.db.session import get_session
from maelstromhub_core import (
    Asset,
    AssetCreate,
    AssetUpdate,
    Candle,
    CandleBackfillRequest,
    Dataset,
    DatasetCreate,
    DatasetUpdate,
    Experiment,
    ExperimentCreate,
    ExperimentUpdate,
    Feature,
    FeatureCreate,
    FeatureUpdate,
    IngestionJob,
    Timeframe,
    TimeframeCreate,
    TimeframeUpdate,
)

router = APIRouter()

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/assets")
async def get_assets(session: SessionDependency) -> dict[str, list[Asset]]:
    return {"assets": await list_assets(session)}


@router.post("/assets", status_code=201)
async def post_asset(payload: AssetCreate, session: SessionDependency) -> Asset:
    return await create_asset(session, payload)


@router.get("/assets/{asset_id}")
async def get_asset_by_id(asset_id: str, session: SessionDependency) -> Asset:
    return await get_asset(session, asset_id)


@router.patch("/assets/{asset_id}")
async def patch_asset(asset_id: str, payload: AssetUpdate, session: SessionDependency) -> Asset:
    return await update_asset(session, asset_id, payload)


@router.delete("/assets/{asset_id}", status_code=204)
async def remove_asset(asset_id: str, session: SessionDependency) -> Response:
    await delete_asset(session, asset_id)
    return Response(status_code=204)


@router.get("/timeframes")
async def get_timeframes(session: SessionDependency) -> dict[str, list[Timeframe]]:
    return {"timeframes": await list_timeframes(session)}


@router.post("/timeframes", status_code=201)
async def post_timeframe(payload: TimeframeCreate, session: SessionDependency) -> Timeframe:
    return await create_timeframe(session, payload)


@router.get("/timeframes/{timeframe_id}")
async def get_timeframe_by_id(timeframe_id: str, session: SessionDependency) -> Timeframe:
    return await get_timeframe(session, timeframe_id)


@router.patch("/timeframes/{timeframe_id}")
async def patch_timeframe(timeframe_id: str, payload: TimeframeUpdate, session: SessionDependency) -> Timeframe:
    return await update_timeframe(session, timeframe_id, payload)


@router.delete("/timeframes/{timeframe_id}", status_code=204)
async def remove_timeframe(timeframe_id: str, session: SessionDependency) -> Response:
    await delete_timeframe(session, timeframe_id)
    return Response(status_code=204)


@router.get("/datasets")
async def get_datasets(session: SessionDependency) -> dict[str, list[Dataset]]:
    return {"datasets": await list_datasets(session)}


@router.post("/datasets", status_code=201)
async def post_dataset(payload: DatasetCreate, session: SessionDependency) -> Dataset:
    return await create_dataset(session, payload)


@router.post("/datasets/{dataset_id}/backfill-candles")
async def post_dataset_candle_backfill(
    dataset_id: str,
    payload: CandleBackfillRequest,
    session: SessionDependency,
) -> IngestionJob:
    return await enqueue_dataset_candle_backfill(session, dataset_id, payload)


@router.get("/datasets/{dataset_id}/candles")
async def get_dataset_candles(dataset_id: str, session: SessionDependency) -> dict[str, list[Candle]]:
    return {"candles": await list_dataset_candles(session, dataset_id)}


@router.get("/datasets/{dataset_id}/ingestion-jobs")
async def get_dataset_ingestion_jobs(dataset_id: str, session: SessionDependency) -> dict[str, list[IngestionJob]]:
    return {"ingestion_jobs": await list_dataset_ingestion_jobs(session, dataset_id)}


@router.get("/datasets/{dataset_id}")
async def get_dataset_by_id(dataset_id: str, session: SessionDependency) -> Dataset:
    return await get_dataset(session, dataset_id)


@router.patch("/datasets/{dataset_id}")
async def patch_dataset(dataset_id: str, payload: DatasetUpdate, session: SessionDependency) -> Dataset:
    return await update_dataset(session, dataset_id, payload)


@router.delete("/datasets/{dataset_id}", status_code=204)
async def remove_dataset(dataset_id: str, session: SessionDependency) -> Response:
    await delete_dataset(session, dataset_id)
    return Response(status_code=204)


@router.get("/ingestion-jobs/{job_id}")
async def get_ingestion_job_by_id(job_id: str, session: SessionDependency) -> IngestionJob:
    return await get_ingestion_job(session, job_id)


@router.get("/features")
async def get_features(session: SessionDependency) -> dict[str, list[Feature]]:
    return {"features": await list_features(session)}


@router.post("/features", status_code=201)
async def post_feature(payload: FeatureCreate, session: SessionDependency) -> Feature:
    return await create_feature(session, payload)


@router.get("/features/{feature_id}")
async def get_feature_by_id(feature_id: str, session: SessionDependency) -> Feature:
    return await get_feature(session, feature_id)


@router.patch("/features/{feature_id}")
async def patch_feature(feature_id: str, payload: FeatureUpdate, session: SessionDependency) -> Feature:
    return await update_feature(session, feature_id, payload)


@router.delete("/features/{feature_id}", status_code=204)
async def remove_feature(feature_id: str, session: SessionDependency) -> Response:
    await delete_feature(session, feature_id)
    return Response(status_code=204)


@router.get("/experiments")
async def get_experiments(session: SessionDependency) -> dict[str, list[Experiment]]:
    return {"experiments": await list_experiments(session)}


@router.post("/experiments", status_code=201)
async def post_experiment(payload: ExperimentCreate, session: SessionDependency) -> Experiment:
    return await create_experiment(session, payload)


@router.get("/experiments/{experiment_id}")
async def get_experiment_by_id(experiment_id: str, session: SessionDependency) -> Experiment:
    return await get_experiment(session, experiment_id)


@router.patch("/experiments/{experiment_id}")
async def patch_experiment(experiment_id: str, payload: ExperimentUpdate, session: SessionDependency) -> Experiment:
    return await update_experiment(session, experiment_id, payload)


@router.delete("/experiments/{experiment_id}", status_code=204)
async def remove_experiment(experiment_id: str, session: SessionDependency) -> Response:
    await delete_experiment(session, experiment_id)
    return Response(status_code=204)
