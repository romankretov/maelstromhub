from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.research_repositories import (
    create_asset,
    create_dataset,
    create_timeframe,
    enqueue_dataset_candle_backfill,
    enqueue_dataset_feature_compute,
    get_feature_summary,
    get_dataset,
    list_feature_snapshots,
    list_dataset_candles,
    run_ingestion_job,
)
from app.db.models import FeatureSnapshotORM
from app.db.repositories import create_strategy
from app.db.session import get_session
from app.db.strategy_repositories import (
    create_strategy_version,
    list_strategy_version_signals,
    run_strategy_version_signals,
)
from app.main import app
from app.providers.candles import ProviderCandle
from maelstromhub_core import (
    AssetCreate,
    CandleBackfillRequest,
    DatasetCreate,
    FeatureComputeRequest,
    StrategyCreate,
    StrategyVersionCreate,
    TimeframeCreate,
)


class AsyncSessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._session.execute(*args, **kwargs)

    def add(self, *args: Any, **kwargs: Any) -> None:
        self._session.add(*args, **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Any:
        return self._session.get(*args, **kwargs)

    async def delete(self, instance: object) -> None:
        self._session.delete(instance)

    async def flush(self) -> None:
        self._session.flush()

    async def commit(self) -> None:
        self._session.commit()

    async def refresh(self, instance: object) -> None:
        self._session.refresh(instance)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)

    Base.metadata.create_all(engine)

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


class FakeCandleProvider:
    name = "fake"

    async def get_historical_candles(self, **_: Any) -> list[ProviderCandle]:
        from datetime import UTC, datetime

        return [
            ProviderCandle(
                opened_at=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=12.5,
                trade_count=4,
            ),
            ProviderCandle(
                opened_at=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
                open=105.0,
                high=112.0,
                low=102.0,
                close=109.0,
                volume=15.0,
                trade_count=6,
            ),
        ]


class LongFakeCandleProvider:
    name = "fake"

    async def get_historical_candles(self, **_: Any) -> list[ProviderCandle]:
        from datetime import UTC, datetime, timedelta

        start = datetime(2026, 1, 1, tzinfo=UTC)
        candles: list[ProviderCandle] = []
        for index in range(60):
            close = float(index + 1)
            candles.append(
                ProviderCandle(
                    opened_at=start + timedelta(hours=index),
                    open=close,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    volume=100.0 + index,
                )
            )
        return candles

@pytest.mark.anyio
async def test_ideas_start_empty(client: httpx.AsyncClient) -> None:
    response = await client.get("/ideas")

    assert response.status_code == 200
    assert response.json() == {"ideas": []}


@pytest.mark.anyio
async def test_create_idea_persists_and_audits(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/ideas",
        json={
            "title": "Funding rate mean reversion",
            "thesis": "Track persistent funding dislocations before strategy design.",
        },
    )

    assert response.status_code == 201
    idea = response.json()
    assert idea["id"].startswith("idea-")
    assert idea["title"] == "Funding rate mean reversion"

    list_response = await client.get("/ideas")
    assert list_response.json()["ideas"][0]["id"] == idea["id"]

    audit_response = await client.get("/audit-events")
    audit_events = audit_response.json()["audit_events"]
    assert audit_events[0]["action"] == "created_idea"
    assert audit_events[0]["subject"] == idea["id"]


@pytest.mark.anyio
async def test_create_strategy_draft_from_idea(client: httpx.AsyncClient) -> None:
    idea_response = await client.post(
        "/ideas",
        json={
            "title": "Breakout follow-through filter",
            "thesis": "Explore high-volume breakout continuation.",
        },
    )
    idea = idea_response.json()

    response = await client.post(
        "/strategies",
        json={
            "name": "Momentum Continuation Study",
            "source_idea_id": idea["id"],
            "description": "Draft strategy shell for research workflow.",
        },
    )

    assert response.status_code == 201
    strategy = response.json()
    assert strategy["id"].startswith("strategy-")
    assert strategy["status"] == "Draft"
    assert strategy["source_idea_id"] == idea["id"]

    list_response = await client.get("/strategies")
    assert list_response.json()["strategies"][0]["id"] == strategy["id"]

    audit_response = await client.get("/audit-events")
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "created_strategy" in actions


@pytest.mark.anyio
async def test_create_standalone_strategy_draft(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/strategies",
        json={
            "name": "Standalone Research Draft",
            "description": "Draft strategy shell without a linked idea.",
        },
    )

    assert response.status_code == 201
    strategy = response.json()
    assert strategy["status"] == "Draft"
    assert strategy["source_idea_id"] is None


@pytest.mark.anyio
async def test_strategy_template_and_version_routes(client: httpx.AsyncClient) -> None:
    _, _, dataset = await create_research_chain(client)
    strategy_response = await client.post(
        "/strategies",
        json={
            "name": "SMA Signal Study",
            "description": "Turns feature snapshots into normalized signals.",
        },
    )
    strategy = strategy_response.json()

    templates_response = await client.get("/strategy-templates")
    templates = templates_response.json()["strategy_templates"]
    version_response = await client.post(
        f"/strategies/{strategy['id']}/versions",
        json={
            "template_id": "sma_crossover",
            "dataset_id": dataset["id"],
            "parameters": {"confidence": 0.8, "suggested_size": 0.5},
        },
    )
    version = version_response.json()
    versions_response = await client.get(f"/strategies/{strategy['id']}/versions")
    run_response = await client.post(f"/strategy-versions/{version['id']}/run-signals")
    signals_response = await client.get(f"/strategy-versions/{version['id']}/signals")

    assert templates_response.status_code == 200
    assert {template["id"] for template in templates} == {"sma_crossover", "rsi_mean_reversion"}
    assert version_response.status_code == 201
    assert version["version_number"] == 1
    assert version["parameters"]["confidence"] == 0.8
    assert versions_response.json()["strategy_versions"][0]["id"] == version["id"]
    assert run_response.json() == {
        "strategy_version_id": version["id"],
        "signals_written": 0,
        "total_signals": 0,
    }
    assert signals_response.json() == {"signals": []}


async def create_research_chain(client: httpx.AsyncClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    asset_response = await client.post(
        "/assets",
        json={"symbol": "BTC", "venue": "hyperliquid", "description": "Bitcoin perpetual"},
    )
    timeframe_response = await client.post(
        "/timeframes",
        json={"name": "One hour", "interval": "1h"},
    )
    asset = asset_response.json()
    timeframe = timeframe_response.json()
    dataset_response = await client.post(
        "/datasets",
        json={
            "asset_id": asset["id"],
            "timeframe_id": timeframe["id"],
            "name": "BTC 1h research dataset",
            "description": "Placeholder dataset metadata only.",
        },
    )

    assert asset_response.status_code == 201
    assert timeframe_response.status_code == 201
    assert dataset_response.status_code == 201
    return asset, timeframe, dataset_response.json()


@pytest.mark.anyio
async def test_research_crud_chain(client: httpx.AsyncClient) -> None:
    asset, timeframe, dataset = await create_research_chain(client)

    feature_response = await client.post(
        "/features",
        json={
            "dataset_id": dataset["id"],
            "name": "Volatility snapshot",
            "values": {"realized_volatility": 0.42},
            "description": "Feature snapshot placeholder.",
        },
    )
    feature = feature_response.json()

    experiment_response = await client.post(
        "/experiments",
        json={
            "dataset_id": dataset["id"],
            "feature_id": feature["id"],
            "name": "Funding volatility study",
            "hypothesis": "Volatility regimes may improve funding-rate research filters.",
            "notes": "No backtest connected.",
            "metrics": {"sample_count": 0},
        },
    )
    experiment = experiment_response.json()

    assert feature_response.status_code == 201
    assert experiment_response.status_code == 201
    assert asset["id"].startswith("asset-")
    assert timeframe["id"].startswith("timeframe-")
    assert dataset["asset_id"] == asset["id"]
    assert feature["dataset_id"] == dataset["id"]
    assert experiment["status"] == "Draft"
    assert experiment["feature_id"] == feature["id"]

    list_response = await client.get("/experiments")
    assert list_response.json()["experiments"][0]["id"] == experiment["id"]


@pytest.mark.anyio
async def test_research_update_get_and_delete(client: httpx.AsyncClient) -> None:
    asset, _, _ = await create_research_chain(client)

    patch_response = await client.patch(
        f"/assets/{asset['id']}",
        json={"description": "Updated metadata"},
    )
    get_response = await client.get(f"/assets/{asset['id']}")
    delete_response = await client.delete(f"/assets/{asset['id']}")
    missing_response = await client.get(f"/assets/{asset['id']}")

    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Updated metadata"
    assert get_response.status_code == 200
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_backfill_endpoint_queues_ingestion_job(client: httpx.AsyncClient) -> None:
    _, _, dataset = await create_research_chain(client)

    response = await client.post(f"/datasets/{dataset['id']}/backfill-candles", json={})
    job = response.json()
    job_response = await client.get(f"/ingestion-jobs/{job['id']}")
    dataset_jobs_response = await client.get(f"/datasets/{dataset['id']}/ingestion-jobs")
    audit_response = await client.get("/audit-events")

    assert response.status_code == 200
    assert job["id"].startswith("ingestion-job-")
    assert job["status"] == "queued"
    assert job_response.json()["id"] == job["id"]
    assert dataset_jobs_response.json()["ingestion_jobs"][0]["id"] == job["id"]
    assert audit_response.json()["audit_events"][0]["action"] == "queued_ingestion_job"


@pytest.mark.anyio
async def test_compute_features_endpoint_queues_feature_job(client: httpx.AsyncClient) -> None:
    _, _, dataset = await create_research_chain(client)

    response = await client.post(f"/datasets/{dataset['id']}/compute-features", json={})
    snapshots_response = await client.get(f"/datasets/{dataset['id']}/feature-snapshots")
    summary_response = await client.get(f"/datasets/{dataset['id']}/feature-summary")

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["job_type"] == "feature_compute"
    assert snapshots_response.json() == {"feature_snapshots": []}
    assert summary_response.json()["total_snapshots"] == 0


@pytest.mark.anyio
async def test_worker_execution_backfills_candles_idempotently_and_audits() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        asset = await create_asset(
            session,
            AssetCreate(symbol="BTC", venue="hyperliquid", description="Bitcoin perpetual"),
        )
        timeframe = await create_timeframe(session, TimeframeCreate(name="One hour", interval="1h"))
        dataset = await create_dataset(
            session,
            DatasetCreate(
                asset_id=asset.id,
                timeframe_id=timeframe.id,
                name="BTC 1h research dataset",
                description="Dataset metadata only.",
            ),
        )
        first_job = await enqueue_dataset_candle_backfill(session, dataset.id, CandleBackfillRequest())
        second_job = await enqueue_dataset_candle_backfill(session, dataset.id, CandleBackfillRequest())

        first_result = await run_ingestion_job(session, first_job.id, FakeCandleProvider())
        second_result = await run_ingestion_job(session, second_job.id, FakeCandleProvider())
        candles = await list_dataset_candles(session, dataset.id)
        updated_dataset = await get_dataset(session, dataset.id)

    engine.dispose()

    assert first_result.status == "succeeded"
    assert first_result.candles_written == 2
    assert second_result.status == "succeeded"
    assert second_result.candles_written == 2
    assert len(candles) == 2
    assert candles[0].close == 105.0
    assert updated_dataset.candle_count == 2
    assert updated_dataset.last_ingestion_status == "succeeded"


@pytest.mark.anyio
async def test_worker_execution_computes_features_idempotently() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        asset = await create_asset(session, AssetCreate(symbol="BTC", venue="hyperliquid"))
        timeframe = await create_timeframe(session, TimeframeCreate(name="One hour", interval="1h"))
        dataset = await create_dataset(
            session,
            DatasetCreate(asset_id=asset.id, timeframe_id=timeframe.id, name="BTC 1h research dataset"),
        )
        candle_job = await enqueue_dataset_candle_backfill(session, dataset.id, CandleBackfillRequest())
        await run_ingestion_job(session, candle_job.id, LongFakeCandleProvider())

        first_feature_job = await enqueue_dataset_feature_compute(session, dataset.id, FeatureComputeRequest())
        second_feature_job = await enqueue_dataset_feature_compute(session, dataset.id, FeatureComputeRequest())
        first_result = await run_ingestion_job(session, first_feature_job.id, LongFakeCandleProvider())
        second_result = await run_ingestion_job(session, second_feature_job.id, LongFakeCandleProvider())
        snapshots = await list_feature_snapshots(session, dataset.id)
        summary = await get_feature_summary(session, dataset.id)

    engine.dispose()

    assert first_result.status == "succeeded"
    assert first_result.feature_snapshots_written > 0
    assert second_result.status == "succeeded"
    assert second_result.feature_snapshots_written == first_result.feature_snapshots_written
    assert len(snapshots) == summary.total_snapshots
    assert {item.feature_name for item in summary.features} == {
        "returns_1",
        "returns_5",
        "sma_20",
        "sma_50",
        "volatility_20",
        "rsi_14",
        "atr_14",
    }


@pytest.mark.anyio
async def test_strategy_runner_generates_idempotent_sma_signals() -> None:
    from datetime import UTC, datetime, timedelta

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        asset = await create_asset(session, AssetCreate(symbol="BTC", venue="hyperliquid"))
        timeframe = await create_timeframe(session, TimeframeCreate(name="One hour", interval="1h"))
        dataset = await create_dataset(
            session,
            DatasetCreate(asset_id=asset.id, timeframe_id=timeframe.id, name="BTC 1h research dataset"),
        )
        strategy = await create_strategy(
            session,
            StrategyCreate(name="SMA signal study", description="Feature-snapshot signal generation."),
        )
        start = datetime(2026, 1, 1, tzinfo=UTC)
        for timestamp, fast, slow in [
            (start, 10.0, 20.0),
            (start + timedelta(hours=1), 30.0, 20.0),
        ]:
            session.add(
                FeatureSnapshotORM(
                    id=f"feature-snapshot-{timestamp.hour}-fast",
                    dataset_id=dataset.id,
                    timestamp=timestamp,
                    feature_name="sma_20",
                    numeric_value=fast,
                    metadata_json={},
                )
            )
            session.add(
                FeatureSnapshotORM(
                    id=f"feature-snapshot-{timestamp.hour}-slow",
                    dataset_id=dataset.id,
                    timestamp=timestamp,
                    feature_name="sma_50",
                    numeric_value=slow,
                    metadata_json={},
                )
            )
        await session.commit()

        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(
                template_id="sma_crossover",
                dataset_id=dataset.id,
                parameters={"confidence": 0.9, "suggested_size": 0.25},
            ),
        )
        first_result = await run_strategy_version_signals(session, version.id)
        second_result = await run_strategy_version_signals(session, version.id)
        signals = await list_strategy_version_signals(session, version.id)

    engine.dispose()

    assert first_result.signals_written == 2
    assert second_result.signals_written == 2
    assert second_result.total_signals == 2
    assert [signal.side for signal in reversed(signals)] == ["short", "long"]
    assert all(signal.confidence == 0.9 for signal in signals)
    assert all(signal.suggested_size == 0.25 for signal in signals)
