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


class ResearchRun(BaseModel):
    id: str
    name: str
    status: ResearchRunStatus = ResearchRunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
