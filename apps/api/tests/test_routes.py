from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app


class AsyncSessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._session.execute(*args, **kwargs)

    def add(self, *args: Any, **kwargs: Any) -> None:
        self._session.add(*args, **kwargs)

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
