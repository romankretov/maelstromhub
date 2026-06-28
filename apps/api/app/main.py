from fastapi import FastAPI

from app.config import settings
from maelstromhub_core import AssetSymbol, AuditEvent, Idea, Strategy, StrategyStatus

app = FastAPI(
    title="Maelstromhub API",
    version="0.1.0",
    description="Research and operations API for Maelstromhub.",
)


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


@app.get("/ideas")
async def list_ideas() -> dict[str, list[Idea]]:
    return {
        "ideas": [
            Idea(
                id="idea-001",
                title="Funding rate mean reversion",
                thesis="Track persistent funding dislocations before promoting to strategy design.",
            ),
            Idea(
                id="idea-002",
                title="Breakout follow-through filter",
                thesis="Explore whether high-volume breakouts sustain after volatility normalization.",
            ),
        ]
    }


@app.get("/strategies")
async def list_strategies() -> dict[str, list[Strategy]]:
    return {
        "strategies": [
            Strategy(
                id="strategy-001",
                name="Funding Fade Prototype",
                status=StrategyStatus.DRAFT,
                source_idea_id="idea-001",
                description="Research-only placeholder for a possible funding-rate strategy.",
            ),
            Strategy(
                id="strategy-002",
                name="Momentum Continuation Study",
                status=StrategyStatus.BACKTESTED,
                source_idea_id="idea-002",
                description="Placeholder strategy card for workflow navigation.",
            ),
            Strategy(
                id="strategy-003",
                name="Basis Watchlist",
                status=StrategyStatus.PAPER_TRADING,
                description="Paper-trading placeholder without live execution.",
            ),
        ]
    }


@app.get("/audit-events")
async def list_audit_events() -> dict[str, list[AuditEvent]]:
    return {
        "audit_events": [
            AuditEvent(
                id="audit-001",
                actor="system",
                action="created_product_shell",
                subject="guided_workflow",
            ),
            AuditEvent(
                id="audit-002",
                actor="system",
                action="blocked_live_trading",
                subject="execution_layer",
            ),
        ]
    }
