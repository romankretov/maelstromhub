from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResearchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetSymbol(DomainModel):
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


class IdeaCreate(DomainModel):
    title: str
    thesis: str


class Idea(IdeaCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyCreate(DomainModel):
    name: str
    source_idea_id: str | None = None
    description: str


class Strategy(StrategyCreate):
    id: str
    status: StrategyStatus = StrategyStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(DomainModel):
    id: str
    actor: str
    action: str
    subject: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchRun(DomainModel):
    id: str
    name: str
    status: ResearchRunStatus = ResearchRunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
