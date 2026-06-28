from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.research_repositories import ensure_system_timeframes
from app.db.session import async_session_factory
from app.routes.research import router as research_router
from app.routes.workflow import router as workflow_router
from maelstromhub_core import AssetSymbol


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with async_session_factory() as session:
        await ensure_system_timeframes(session)
    yield


app = FastAPI(
    title="Maelstromhub API",
    version="0.1.0",
    description="Research and operations API for Maelstromhub.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(research_router)
app.include_router(workflow_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/v1/markets")
async def list_markets() -> dict[str, list[AssetSymbol]]:
    return {
        "markets": [
            AssetSymbol(symbol="BTC"),
            AssetSymbol(symbol="ETH"),
            AssetSymbol(symbol="SOL"),
        ]
    }
