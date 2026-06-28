import httpx
import pytest

from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_list_ideas() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ideas")

    assert response.status_code == 200
    body = response.json()
    assert body["ideas"][0]["id"] == "idea-001"


@pytest.mark.anyio
async def test_list_strategies() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/strategies")

    assert response.status_code == 200
    body = response.json()
    statuses = {strategy["status"] for strategy in body["strategies"]}
    assert {"Draft", "Backtested", "Paper Trading"}.issubset(statuses)


@pytest.mark.anyio
async def test_list_audit_events() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/audit-events")

    assert response.status_code == 200
    body = response.json()
    assert "audit_events" in body
    assert body["audit_events"][0]["actor"] == "system"
