from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetSymbol(BaseModel):
    venue: str = Field(default="hyperliquid")
    symbol: str


class StrategyStatus(StrEnum):
    DRAFT = "Draft"
    BACKTESTED = "Backtested"
    PAPER_TRADING = "Paper Trading"
    LIVE_SMALL_SIZE = "Live Small Size"
    LIVE_FULL_SIZE = "Live Full Size"
    PAUSED = "Paused"
    RETIRED = "Retired"


class Idea(BaseModel):
    id: str
    title: str
    thesis: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Strategy(BaseModel):
    id: str
    name: str
    status: StrategyStatus = StrategyStatus.DRAFT
    source_idea_id: str | None = None
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(BaseModel):
    id: str
    actor: str
    action: str
    subject: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchRun(BaseModel):
    id: str
    name: str
    status: ResearchRunStatus = ResearchRunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
