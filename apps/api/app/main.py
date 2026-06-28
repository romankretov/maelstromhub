from fastapi import FastAPI

from app.config import settings
from app.routes.workflow import router as workflow_router
from maelstromhub_core import AssetSymbol

app = FastAPI(
    title="Maelstromhub API",
    version="0.1.0",
    description="Research and operations API for Maelstromhub.",
)
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

