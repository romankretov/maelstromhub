from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.research_repositories import (
    create_asset,
    create_dataset,
    enqueue_dataset_candle_backfill,
    enqueue_dataset_feature_compute,
    ensure_system_timeframes,
    get_feature_summary,
    get_dataset,
    list_feature_snapshots,
    list_dataset_candles,
    run_ingestion_job,
)
from app.db.models import BacktestRunORM, CandleORM, FeatureSnapshotORM, MarketRegimeSnapshotORM, SignalORM, StrategyORM
from app.db.paper_repositories import create_paper_account, create_paper_deployment
from app.db.repositories import create_strategy
from app.db.session import get_session
from app.db.strategy_repositories import (
    SMA_CROSSOVER_TEMPLATE_ID,
    create_strategy_version,
    list_strategy_version_signals,
    run_strategy_version_signals,
)
from app.main import app
from app.market_intelligence.engine import RegimeEngine
from app.providers.candles import ProviderCandle
from maelstromhub_core import (
    AssetCreate,
    CandleBackfillRequest,
    DatasetCreate,
    FeatureComputeRequest,
    IdeaCreate,
    PaperAccountCreate,
    PaperDeploymentCreate,
    TrendRegime,
    StrategyCreate,
    StrategyVersionCreate,
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
    assert UUID(idea["id"])
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
    assert UUID(strategy["id"])
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
    sma_template = next(template for template in templates if template["name"] == "SMA crossover")
    version_response = await client.post(
        f"/strategies/{strategy['id']}/versions",
        json={
            "template_id": sma_template["id"],
            "dataset_id": dataset["id"],
            "parameters": {"confidence": 0.8, "suggested_size": 0.5},
        },
    )
    version = version_response.json()
    versions_response = await client.get(f"/strategies/{strategy['id']}/versions")
    run_response = await client.post(f"/strategy-versions/{version['id']}/run-signals")
    signals_response = await client.get(f"/strategy-versions/{version['id']}/signals")

    assert templates_response.status_code == 200
    assert {template["name"] for template in templates} == {"SMA crossover", "RSI mean reversion"}
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
    timeframe_response = await client.get("/timeframes")
    asset = asset_response.json()
    timeframe = next(item for item in timeframe_response.json()["timeframes"] if item["interval"] == "1h")
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
    assert timeframe_response.status_code == 200
    assert dataset_response.status_code == 201
    return asset, timeframe, dataset_response.json()


async def _create_research_chain_in_session(
    session: AsyncSessionAdapter,
) -> tuple[Any, Any, Any]:
    asset = await create_asset(session, AssetCreate(symbol="BTC", venue="hyperliquid"))
    timeframe = await _get_one_hour_timeframe(session)
    dataset = await create_dataset(
        session,
        DatasetCreate(asset_id=asset.id, timeframe_id=timeframe.id, name="BTC 1h research dataset"),
    )
    return asset, timeframe, dataset


async def _get_one_hour_timeframe(session: AsyncSessionAdapter) -> Any:
    timeframes = await ensure_system_timeframes(session)
    return next(item for item in timeframes if item.interval == "1h")


@pytest.mark.anyio
async def test_system_timeframes_exist_on_fresh_database(client: httpx.AsyncClient) -> None:
    response = await client.get("/timeframes")
    timeframes = response.json()["timeframes"]

    assert response.status_code == 200
    assert [timeframe["interval"] for timeframe in timeframes] == ["1m", "5m", "15m", "1h", "4h", "1d"]
    assert all(UUID(timeframe["id"]) for timeframe in timeframes)
    assert all(timeframe["description"] == "System-supported exchange timeframe." for timeframe in timeframes)


@pytest.mark.anyio
async def test_dataset_creation_uses_default_timeframe(client: httpx.AsyncClient) -> None:
    asset_response = await client.post("/assets", json={"symbol": "ETH", "venue": "hyperliquid"})
    timeframes_response = await client.get("/timeframes")
    one_hour = next(timeframe for timeframe in timeframes_response.json()["timeframes"] if timeframe["interval"] == "1h")

    dataset_response = await client.post(
        "/datasets",
        json={
            "asset_id": asset_response.json()["id"],
            "timeframe_id": one_hour["id"],
            "name": "ETH 1h research dataset",
        },
    )

    assert asset_response.status_code == 201
    assert timeframes_response.status_code == 200
    assert dataset_response.status_code == 201
    assert dataset_response.json()["timeframe_id"] == one_hour["id"]


@pytest.mark.anyio
async def test_workspace_load_market_creates_dataset_on_fresh_database(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/workspace/load-market",
        json={"symbol": "btc", "timeframe": "1h", "range": "7d"},
    )
    body = response.json()
    datasets_response = await client.get("/datasets")

    assert response.status_code == 200
    assert UUID(body["dataset_id"])
    assert body["market"]["symbol"] == "BTC"
    assert body["market"]["timeframe"] == "1h"
    assert body["data_health"]["status"] == "queued"
    assert body["data_health"]["queued_jobs"] == 1
    assert datasets_response.json()["datasets"][0]["id"] == body["dataset_id"]


@pytest.mark.anyio
async def test_workspace_load_market_auto_seeds_timeframes(client: httpx.AsyncClient) -> None:
    load_response = await client.post(
        "/workspace/load-market",
        json={"symbol": "SOL", "timeframe": "4h", "range": "30d"},
    )
    timeframes_response = await client.get("/timeframes")

    assert load_response.status_code == 200
    assert [timeframe["interval"] for timeframe in timeframes_response.json()["timeframes"]] == [
        "1m",
        "5m",
        "15m",
        "1h",
        "4h",
        "1d",
    ]


@pytest.mark.anyio
async def test_workspace_users_do_not_need_to_create_timeframes(client: httpx.AsyncClient) -> None:
    load_response = await client.post(
        "/workspace/load-market",
        json={"symbol": "HYPE", "timeframe": "15m", "range": "90d"},
    )
    timeframes_response = await client.get("/timeframes")
    dataset_response = await client.get(f"/datasets/{load_response.json()['dataset_id']}")
    selected_timeframe = next(
        timeframe for timeframe in timeframes_response.json()["timeframes"] if timeframe["interval"] == "15m"
    )

    assert load_response.status_code == 200
    assert dataset_response.status_code == 200
    assert dataset_response.json()["timeframe_id"] == selected_timeframe["id"]


@pytest.mark.anyio
async def test_workspace_notes_crud(client: httpx.AsyncClient) -> None:
    create_response = await client.post(
        "/workspace/notes",
        json={
            "symbol": "btc",
            "timeframe": "1h",
            "title": "Momentum hypothesis",
            "body": "## Hypothesis\nBTC trend continues.\n\n## Observations\n\n## Conclusion\n",
        },
    )
    note = create_response.json()
    list_response = await client.get("/workspace/notes?symbol=BTC&timeframe=1h")
    update_response = await client.patch(
        f"/workspace/notes/{note['id']}",
        json={"title": "Updated hypothesis", "body": "## Conclusion\nWait for confirmation."},
    )
    delete_response = await client.delete(f"/workspace/notes/{note['id']}")
    empty_response = await client.get("/workspace/notes?symbol=BTC&timeframe=1h")

    assert create_response.status_code == 201
    assert UUID(note["id"])
    assert note["symbol"] == "BTC"
    assert note["timeframe"] == "1h"
    assert list_response.json()["workspace_notes"][0]["id"] == note["id"]
    assert update_response.json()["title"] == "Updated hypothesis"
    assert delete_response.status_code == 204
    assert empty_response.json() == {"workspace_notes": []}


@pytest.mark.anyio
async def test_workspace_run_backtest_orchestrates_strategy_signals_and_backtest() -> None:
    from datetime import UTC, datetime, timedelta

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
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
            load_response = await test_client.post(
                "/workspace/load-market",
                json={"symbol": "BTC", "timeframe": "1h", "range": "90d"},
            )
            dataset_id = UUID(load_response.json()["dataset_id"])
            with session_factory() as sync_session:
                start = datetime(2026, 1, 1, tzinfo=UTC)
                for index in range(80):
                    close = 100.0 + index
                    sync_session.add(
                        CandleORM(
                            dataset_id=dataset_id,
                            opened_at=start + timedelta(hours=index),
                            open=close - 0.5,
                            high=close + 1.0,
                            low=close - 1.0,
                            close=close,
                            volume=1000.0 + index,
                            trade_count=index + 1,
                        )
                    )
                sync_session.commit()

            state_response = await test_client.get("/workspace/state?symbol=BTC&timeframe=1h&range=90d")
            template = next(
                item
                for item in state_response.json()["available_strategy_templates"]
                if item["name"].lower().startswith("sma")
            )
            response = await test_client.post(
                "/workspace/run-backtest",
                json={
                    "symbol": "BTC",
                    "timeframe": "1h",
                    "range": "90d",
                    "template_id": template["id"],
                    "parameters": {"fast_window": 20, "slow_window": 50, "confidence": 0.8, "suggested_size": 1.0},
                    "starting_balance": 10000,
                    "fee_bps": 5,
                    "slippage_bps": 2,
                    "allowed_regimes": None,
                },
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    body = response.json()
    assert response.status_code == 200
    assert UUID(body["backtest"]["id"])
    assert body["backtest"]["status"] == "succeeded"
    assert body["signals_written"] > 0
    assert body["total_signals"] > 0
    assert body["evaluation"]["verdict"] in {"Ready", "Review", "Blocked"}
    assert body["workspace_state"]["latest_backtests"][0]["id"] == body["backtest"]["id"]


@pytest.mark.anyio
async def test_workspace_run_backtest_blocks_until_candles_exist(client: httpx.AsyncClient) -> None:
    load_response = await client.post(
        "/workspace/load-market",
        json={"symbol": "ETH", "timeframe": "1h", "range": "7d"},
    )
    template = load_response.json()["available_strategy_templates"][0]

    response = await client.post(
        "/workspace/run-backtest",
        json={
            "symbol": "ETH",
            "timeframe": "1h",
            "range": "7d",
            "template_id": template["id"],
            "parameters": {},
            "starting_balance": 10000,
            "fee_bps": 5,
            "slippage_bps": 2,
        },
    )

    assert response.status_code == 409
    assert "Candles are not loaded yet" in response.json()["detail"]


@pytest.mark.anyio
async def test_workspace_paper_deploy_starts_from_latest_backtest() -> None:
    from datetime import UTC, datetime, timedelta

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
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
            load_response = await test_client.post(
                "/workspace/load-market",
                json={"symbol": "BTC", "timeframe": "1h", "range": "90d"},
            )
            dataset_id = UUID(load_response.json()["dataset_id"])
            with session_factory() as sync_session:
                start = datetime(2026, 1, 1, tzinfo=UTC)
                for index in range(80):
                    close = 100.0 + index
                    sync_session.add(
                        CandleORM(
                            dataset_id=dataset_id,
                            opened_at=start + timedelta(hours=index),
                            open=close - 0.5,
                            high=close + 1.0,
                            low=close - 1.0,
                            close=close,
                            volume=1000.0 + index,
                            trade_count=index + 1,
                        )
                    )
                sync_session.commit()

            state_response = await test_client.get("/workspace/state?symbol=BTC&timeframe=1h&range=90d")
            template = next(
                item
                for item in state_response.json()["available_strategy_templates"]
                if item["name"].lower().startswith("sma")
            )
            backtest_response = await test_client.post(
                "/workspace/run-backtest",
                json={
                    "symbol": "BTC",
                    "timeframe": "1h",
                    "range": "90d",
                    "template_id": template["id"],
                    "parameters": {"fast_window": 20, "slow_window": 50, "confidence": 0.8, "suggested_size": 1.0},
                    "starting_balance": 10000,
                    "fee_bps": 5,
                    "slippage_bps": 2,
                    "allowed_regimes": None,
                },
            )
            account_response = await test_client.post(
                "/paper/accounts",
                json={"name": "Workspace deploy account", "starting_balance": 10000},
            )
            deploy_response = await test_client.post(
                "/workspace/paper-deploy",
                json={
                    "backtest_id": backtest_response.json()["backtest"]["id"],
                    "paper_account_id": account_response.json()["id"],
                },
            )
            step_response = await test_client.post(f"/paper/deployments/{deploy_response.json()['id']}/step")
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    backtest = backtest_response.json()["backtest"]
    deployment = deploy_response.json()
    assert backtest_response.status_code == 200
    assert backtest["status"] == "succeeded"
    assert account_response.status_code == 201
    assert deploy_response.status_code == 201
    assert deployment["status"] == "running"
    assert deployment["strategy_version_id"] == backtest["strategy_version_id"]
    assert deployment["paper_account_id"] == account_response.json()["id"]
    assert step_response.status_code == 200


@pytest.mark.anyio
async def test_workspace_optimise_runs_ranked_backtests() -> None:
    from datetime import UTC, datetime, timedelta

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
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
            load_response = await test_client.post(
                "/workspace/load-market",
                json={"symbol": "BTC", "timeframe": "1h", "range": "90d"},
            )
            dataset_id = UUID(load_response.json()["dataset_id"])
            with session_factory() as sync_session:
                start = datetime(2026, 1, 1, tzinfo=UTC)
                for index in range(80):
                    close = 100.0 + index
                    sync_session.add(
                        CandleORM(
                            dataset_id=dataset_id,
                            opened_at=start + timedelta(hours=index),
                            open=close - 0.5,
                            high=close + 1.0,
                            low=close - 1.0,
                            close=close,
                            volume=1000.0 + index,
                            trade_count=index + 1,
                        )
                    )
                sync_session.commit()

            state_response = await test_client.get("/workspace/state?symbol=BTC&timeframe=1h&range=90d")
            template = next(
                item
                for item in state_response.json()["available_strategy_templates"]
                if item["name"].lower().startswith("sma")
            )
            response = await test_client.post(
                "/workspace/optimise",
                json={
                    "symbol": "BTC",
                    "timeframe": "1h",
                    "range": "90d",
                    "template_id": template["id"],
                    "parameter_grid": {"fast_window": [10, 20], "slow_window": [40, 60]},
                    "starting_balance": 10000,
                    "fee_bps": 5,
                    "slippage_bps": 2,
                    "allowed_regimes": None,
                },
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    body = response.json()
    assert response.status_code == 200
    assert body["total_combinations"] == 4
    assert [candidate["rank"] for candidate in body["results"]] == [1, 2, 3, 4]
    assert all(candidate["backtest"]["status"] == "succeeded" for candidate in body["results"])
    assert all(candidate["signals_written"] > 0 for candidate in body["results"])


@pytest.mark.anyio
async def test_workspace_optimise_rejects_more_than_fifty_combinations(client: httpx.AsyncClient) -> None:
    load_response = await client.post(
        "/workspace/load-market",
        json={"symbol": "SOL", "timeframe": "1h", "range": "7d"},
    )
    template = load_response.json()["available_strategy_templates"][0]

    response = await client.post(
        "/workspace/optimise",
        json={
            "symbol": "SOL",
            "timeframe": "1h",
            "range": "7d",
            "template_id": template["id"],
            "parameter_grid": {"fast_window": list(range(1, 52)), "slow_window": [100]},
            "starting_balance": 10000,
            "fee_bps": 5,
            "slippage_bps": 2,
        },
    )

    assert response.status_code == 400
    assert "limited to 50 parameter combinations" in response.json()["detail"]


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
    assert UUID(asset["id"])
    assert UUID(timeframe["id"])
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
    assert UUID(job["id"])
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
        timeframe = await _get_one_hour_timeframe(session)
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
        timeframe = await _get_one_hour_timeframe(session)
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
        timeframe = await _get_one_hour_timeframe(session)
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
                    dataset_id=dataset.id,
                    timestamp=timestamp,
                    feature_name="sma_20",
                    numeric_value=fast,
                    metadata_json={},
                )
            )
            session.add(
                FeatureSnapshotORM(
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
                template_id=SMA_CROSSOVER_TEMPLATE_ID,
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


@pytest.mark.anyio
async def test_workflow_chain_keeps_uuid_ids_from_idea_to_paper_deployment() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        _, _, dataset = await _create_research_chain_in_session(session)
        idea = await clientless_create_idea(session)
        strategy = await create_strategy(
            session,
            StrategyCreate(
                name="UUID chain strategy",
                source_idea_id=idea.id,
                description="Ensures UUIDs survive the workflow chain.",
            ),
        )
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(template_id=SMA_CROSSOVER_TEMPLATE_ID, dataset_id=dataset.id),
        )
        backtest = BacktestRunORM(
            strategy_version_id=version.id,
            dataset_id=dataset.id,
            status="succeeded",
            starting_balance=1000,
            fee_bps=0,
            slippage_bps=0,
            metrics={
                "total_return": 0.01,
                "max_drawdown": -0.01,
                "trade_count": 1,
            },
        )
        session.add(backtest)
        strategy_orm = sync_session.get(StrategyORM, strategy.id)
        assert strategy_orm is not None
        strategy_orm.status = "Backtested"
        await session.commit()
        await session.refresh(backtest)

        account = await create_paper_account(session, PaperAccountCreate(name="UUID paper", starting_balance=1000))
        deployment = await create_paper_deployment(
            session,
            PaperDeploymentCreate(
                strategy_id=strategy.id,
                strategy_version_id=version.id,
                paper_account_id=account.id,
            ),
        )

    engine.dispose()

    assert isinstance(idea.id, UUID)
    assert isinstance(strategy.id, UUID)
    assert isinstance(version.id, UUID)
    assert isinstance(version.template_id, UUID)
    assert isinstance(backtest.id, UUID)
    assert isinstance(account.id, UUID)
    assert isinstance(deployment.id, UUID)


async def clientless_create_idea(session: AsyncSessionAdapter):
    from app.db.repositories import create_idea

    return await create_idea(
        session,
        IdeaCreate(
            title="UUID workflow idea",
            thesis="Every workflow entity should use a native UUID identifier.",
        ),
    )


@pytest.mark.anyio
async def test_backtest_run_replays_long_flat_signals_and_persists_results() -> None:
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
        timeframe = await _get_one_hour_timeframe(session)
        dataset = await create_dataset(
            session,
            DatasetCreate(asset_id=asset.id, timeframe_id=timeframe.id, name="BTC 1h research dataset"),
        )
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Backtest study", description="Deterministic long flat replay."),
        )
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(template_id=SMA_CROSSOVER_TEMPLATE_ID, dataset_id=dataset.id),
        )
        start = datetime(2026, 1, 1, tzinfo=UTC)
        for index, close in enumerate([100.0, 110.0, 120.0]):
            timestamp = start + timedelta(hours=index)
            session.add(
                CandleORM(
                    dataset_id=dataset.id,
                    opened_at=timestamp,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=100.0,
                )
            )
        session.add(
            SignalORM(
                strategy_version_id=version.id,
                strategy_id=strategy.id,
                dataset_id=dataset.id,
                timestamp=start,
                symbol="BTC",
                side="long",
                confidence=1.0,
                reason="enter",
                suggested_size=1.0,
                metadata_json={},
            )
        )
        session.add(
            SignalORM(
                strategy_version_id=version.id,
                strategy_id=strategy.id,
                dataset_id=dataset.id,
                timestamp=start + timedelta(hours=2),
                symbol="BTC",
                side="flat",
                confidence=1.0,
                reason="exit",
                suggested_size=0.0,
                metadata_json={},
            )
        )
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        response = await test_client.post(
            f"/strategy-versions/{version.id}/backtests",
            json={"starting_balance": 1000, "fee_bps": 0, "slippage_bps": 0},
        )
        run = response.json()
        list_response = await test_client.get(f"/strategy-versions/{version.id}/backtests")
        get_response = await test_client.get(f"/backtests/{run['id']}")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    assert response.status_code == 201
    assert run["status"] == "succeeded"
    assert run["metrics"]["trade_count"] == 1
    assert run["metrics"]["win_rate"] == 1.0
    assert run["metrics"]["total_return"] == 0.2
    assert run["trades"][0]["pnl"] == 200.0
    assert len(run["equity_curve"]) == 3
    assert list_response.json()["backtests"][0]["id"] == run["id"]
    assert get_response.json()["id"] == run["id"]
    assert {event["action"] for event in audit_response.json()["audit_events"]} >= {
        "started_backtest",
        "succeeded_backtest",
    }


@pytest.mark.anyio
async def test_promote_strategy_to_backtested_when_backtest_gate_passes() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        _, _, dataset = await _create_research_chain_in_session(session)
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Promotion candidate", description="Backtest gate should pass."),
        )
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(template_id=SMA_CROSSOVER_TEMPLATE_ID, dataset_id=dataset.id),
        )
        session.add(
            BacktestRunORM(
                strategy_version_id=version.id,
                dataset_id=dataset.id,
                status="succeeded",
                starting_balance=1000,
                fee_bps=0,
                slippage_bps=0,
                metrics={
                    "total_return": 0.12,
                    "max_drawdown": -0.04,
                    "win_rate": 0.6,
                    "trade_count": 5,
                    "profit_factor": 1.8,
                },
            )
        )
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        response = await test_client.post(f"/strategies/{strategy.id}/promote")
        strategies_response = await test_client.get("/strategies")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    result = response.json()
    assert response.status_code == 200
    assert result["promoted"] is True
    assert result["from_status"] == "Draft"
    assert result["to_status"] == "Backtested"
    assert result["evaluation"]["verdict"] == "Ready"
    assert strategies_response.json()["strategies"][0]["status"] == "Backtested"
    assert audit_response.json()["audit_events"][0]["action"] == "promoted_strategy_to_backtested"


@pytest.mark.anyio
async def test_promote_strategy_blocks_with_human_readable_reasons() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        _, _, dataset = await _create_research_chain_in_session(session)
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Promotion reject", description="Backtest gate should block."),
        )
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(template_id=SMA_CROSSOVER_TEMPLATE_ID, dataset_id=dataset.id),
        )
        session.add(
            BacktestRunORM(
                strategy_version_id=version.id,
                dataset_id=dataset.id,
                status="succeeded",
                starting_balance=1000,
                fee_bps=0,
                slippage_bps=0,
                metrics={
                    "total_return": -0.2,
                    "max_drawdown": -0.35,
                    "win_rate": 0.0,
                    "trade_count": 0,
                    "profit_factor": 0.0,
                },
            )
        )
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        response = await test_client.post(f"/strategies/{strategy.id}/promote")
        strategies_response = await test_client.get("/strategies")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    result = response.json()
    assert response.status_code == 200
    assert result["promoted"] is False
    assert result["strategy"]["status"] == "Draft"
    assert result["evaluation"]["verdict"] == "Blocked"
    assert len(result["reasons"]) == 3
    assert any("Max drawdown is too deep" in reason for reason in result["reasons"])
    assert any("Trade count is too low" in reason for reason in result["reasons"])
    assert any("Total return is catastrophically negative" in reason for reason in result["reasons"])
    assert strategies_response.json()["strategies"][0]["status"] == "Draft"
    assert audit_response.json()["audit_events"][0]["action"] == "blocked_strategy_promotion"


@pytest.mark.anyio
async def test_promote_backtested_strategy_blocks_paper_trading() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Already backtested", description="Paper trading should stay blocked."),
        )
        strategy_orm = sync_session.get(StrategyORM, strategy.id)
        assert strategy_orm is not None
        strategy_orm.status = "Backtested"
        sync_session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        response = await test_client.post(f"/strategies/{strategy.id}/promote")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    result = response.json()
    assert response.status_code == 200
    assert result["promoted"] is False
    assert result["from_status"] == "Backtested"
    assert result["to_status"] == "Paper Trading"
    assert "Run at least one successful backtest" in result["reasons"][0]
    assert audit_response.json()["audit_events"][0]["action"] == "blocked_strategy_promotion"


@pytest.mark.anyio
async def test_promote_backtested_strategy_to_paper_trading_when_latest_backtest_is_safe() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        _, _, dataset = await _create_research_chain_in_session(session)
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Paper candidate", description="Backtested strategy ready for paper mode."),
        )
        strategy_orm = sync_session.get(StrategyORM, strategy.id)
        assert strategy_orm is not None
        strategy_orm.status = "Backtested"
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(template_id=SMA_CROSSOVER_TEMPLATE_ID, dataset_id=dataset.id),
        )
        session.add(
            BacktestRunORM(
                strategy_version_id=version.id,
                dataset_id=dataset.id,
                status="succeeded",
                starting_balance=1000,
                fee_bps=0,
                slippage_bps=0,
                metrics={
                    "total_return": 0.04,
                    "max_drawdown": -0.03,
                    "win_rate": 0.5,
                    "trade_count": 2,
                    "profit_factor": 1.2,
                },
            )
        )
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        response = await test_client.post(f"/strategies/{strategy.id}/promote")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    result = response.json()
    assert response.status_code == 200
    assert result["promoted"] is True
    assert result["from_status"] == "Backtested"
    assert result["to_status"] == "Paper Trading"
    assert result["strategy"]["status"] == "Paper Trading"
    assert audit_response.json()["audit_events"][0]["action"] == "promoted_strategy_to_paper_trading"


@pytest.mark.anyio
async def test_paper_trading_steps_long_flat_signals_and_tracks_pnl() -> None:
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
        asset, timeframe, dataset = await _create_research_chain_in_session(session)
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Paper rehearsal", description="Manual long flat paper run."),
        )
        strategy_orm = sync_session.get(StrategyORM, strategy.id)
        assert strategy_orm is not None
        strategy_orm.status = "Backtested"
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(template_id=SMA_CROSSOVER_TEMPLATE_ID, dataset_id=dataset.id),
        )
        start = datetime(2026, 1, 1, tzinfo=UTC)
        for index, close in enumerate([100.0, 110.0, 120.0]):
            timestamp = start + timedelta(hours=index)
            session.add(
                CandleORM(
                    dataset_id=dataset.id,
                    opened_at=timestamp,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=100.0,
                )
            )
        session.add(
            SignalORM(
                strategy_version_id=version.id,
                strategy_id=strategy.id,
                dataset_id=dataset.id,
                timestamp=start,
                symbol=asset.symbol,
                side="long",
                confidence=1.0,
                reason="paper enter",
                suggested_size=1.0,
                metadata_json={},
            )
        )
        session.add(
            SignalORM(
                strategy_version_id=version.id,
                strategy_id=strategy.id,
                dataset_id=dataset.id,
                timestamp=start + timedelta(hours=2),
                symbol=asset.symbol,
                side="flat",
                confidence=1.0,
                reason="paper exit",
                suggested_size=0.0,
                metadata_json={},
            )
        )
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        account_response = await test_client.post(
            "/paper/accounts",
            json={"name": "Paper account", "starting_balance": 1000},
        )
        account = account_response.json()
        deployment_response = await test_client.post(
            "/paper/deployments",
            json={
                "strategy_id": str(strategy.id),
                "strategy_version_id": str(version.id),
                "paper_account_id": account["id"],
            },
        )
        deployment = deployment_response.json()
        first_step = await test_client.post(f"/paper/deployments/{deployment['id']}/step")
        second_step = await test_client.post(f"/paper/deployments/{deployment['id']}/step")
        third_step = await test_client.post(f"/paper/deployments/{deployment['id']}/step")
        detail_response = await test_client.get(f"/paper/deployments/{deployment['id']}")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    detail = detail_response.json()
    assert account_response.status_code == 201
    assert deployment_response.status_code == 201
    assert first_step.json()["advanced"] is True
    assert second_step.json()["advanced"] is True
    assert third_step.json()["advanced"] is True
    assert detail["status"] == "running"
    assert detail["account"]["cash_balance"] == 1200.0
    assert detail["account"]["equity"] == 1200.0
    assert detail["positions"][0]["quantity"] == 0.0
    assert detail["positions"][0]["realized_pnl"] == 200.0
    assert [trade["side"] for trade in detail["trades"]] == ["buy", "sell"]
    assert detail["trades"][1]["pnl"] == 200.0
    assert {event["action"] for event in audit_response.json()["audit_events"]} >= {
        "created_paper_account",
        "started_paper_deployment",
        "executed_paper_step",
    }


def test_regime_engine_classifies_deterministic_market_states() -> None:
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 1, 1, tzinfo=UTC)
    snapshots: list[tuple[Any, str, float]] = []
    rows = [
        {"returns_1": 0.01, "returns_5": 0.05, "sma_20": 120.0, "sma_50": 100.0, "volatility_20": 0.10, "rsi_14": 65.0, "atr_14": 1.0},
        {"returns_1": -0.01, "returns_5": -0.05, "sma_20": 80.0, "sma_50": 100.0, "volatility_20": 0.20, "rsi_14": 35.0, "atr_14": 2.0},
        {"returns_1": 0.0, "returns_5": 0.0, "sma_20": 100.0, "sma_50": 100.0, "volatility_20": 0.05, "rsi_14": 50.0, "atr_14": 0.5},
        {"returns_1": -0.04, "returns_5": -0.12, "sma_20": 90.0, "sma_50": 100.0, "volatility_20": 0.80, "rsi_14": 20.0, "atr_14": 8.0},
    ]
    for index, values in enumerate(rows):
        for feature_name, value in values.items():
            snapshots.append((start + timedelta(hours=index), feature_name, value))

    classifications = RegimeEngine().compute(snapshots)

    assert [classification.trend_regime for classification in classifications[:3]] == [
        TrendRegime.UPTREND,
        TrendRegime.DOWNTREND,
        TrendRegime.SIDEWAYS,
    ]
    assert classifications[0].regime_label.startswith("Bull")
    assert classifications[3].volatility_regime == "HIGH"
    assert classifications[3].risk_regime == "STRESSED"
    assert "Volatility" in classifications[3].explanation


@pytest.mark.anyio
async def test_market_intelligence_api_computes_current_regime_and_audits() -> None:
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
        _, _, dataset = await _create_research_chain_in_session(session)
        start = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [
            {"returns_1": -0.01, "returns_5": -0.02, "sma_20": 95.0, "sma_50": 100.0, "volatility_20": 0.25, "rsi_14": 40.0, "atr_14": 2.0},
            {"returns_1": 0.0, "returns_5": 0.0, "sma_20": 100.0, "sma_50": 100.0, "volatility_20": 0.05, "rsi_14": 50.0, "atr_14": 0.5},
            {"returns_1": 0.02, "returns_5": 0.08, "sma_20": 120.0, "sma_50": 100.0, "volatility_20": 0.10, "rsi_14": 65.0, "atr_14": 1.0},
        ]
        for index, values in enumerate(rows):
            timestamp = start + timedelta(hours=index)
            for feature_name, value in values.items():
                session.add(
                    FeatureSnapshotORM(
                        dataset_id=dataset.id,
                        timestamp=timestamp,
                        feature_name=feature_name,
                        numeric_value=value,
                        metadata_json={},
                    )
                )
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSessionAdapter]:
        with session_factory() as session:
            yield AsyncSessionAdapter(session)

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        compute_response = await test_client.post(f"/datasets/{dataset.id}/compute-regimes")
        current_response = await test_client.get(f"/datasets/{dataset.id}/current-regime")
        intelligence_response = await test_client.get(f"/datasets/{dataset.id}/market-intelligence")
        audit_response = await test_client.get("/audit-events")

    app.dependency_overrides.clear()
    engine.dispose()

    assert compute_response.status_code == 200
    assert compute_response.json()["snapshots_written"] == 3
    assert current_response.json()["trend_regime"] == "UPTREND"
    assert intelligence_response.json()["regime"]["regime_label"].startswith("Bull")
    assert {event["action"] for event in audit_response.json()["audit_events"]} >= {
        "started_regime_computation",
        "completed_regime_computation",
    }


@pytest.mark.anyio
async def test_strategy_signal_generation_stores_skipped_signal_when_regime_is_blocked() -> None:
    from datetime import UTC, datetime

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with session_factory() as sync_session:
        session = AsyncSessionAdapter(sync_session)
        _, _, dataset = await _create_research_chain_in_session(session)
        strategy = await create_strategy(
            session,
            StrategyCreate(name="Regime filtered strategy", description="Blocks disallowed market contexts."),
        )
        version = await create_strategy_version(
            session,
            strategy.id,
            StrategyVersionCreate(
                template_id=SMA_CROSSOVER_TEMPLATE_ID,
                dataset_id=dataset.id,
                allowed_regimes=["Bear Trend"],
            ),
        )
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        for feature_name, value in {"sma_20": 120.0, "sma_50": 100.0}.items():
            session.add(
                FeatureSnapshotORM(
                    dataset_id=dataset.id,
                    timestamp=timestamp,
                    feature_name=feature_name,
                    numeric_value=value,
                    metadata_json={},
                )
            )
        session.add(
            MarketRegimeSnapshotORM(
                dataset_id=dataset.id,
                timestamp=timestamp,
                trend_regime="UPTREND",
                volatility_regime="NORMAL",
                liquidity_regime="NORMAL",
                risk_regime="NORMAL",
                regime_label="Bull Trend",
                confidence=0.9,
                explanation="The market is trending upward with moderate volatility.",
                metadata_json={},
            )
        )
        await session.commit()

        result = await run_strategy_version_signals(session, version.id)
        signals = await list_strategy_version_signals(session, version.id)

    engine.dispose()

    assert result.signals_written == 1
    assert signals[0].side == "flat"
    assert signals[0].metadata["skipped"] is True
    assert signals[0].metadata["skip_reason"] == "Blocked by regime filter."
