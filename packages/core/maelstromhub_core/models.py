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


class AssetCreate(DomainModel):
    symbol: str
    venue: str = "hyperliquid"
    description: str | None = None


class Asset(AssetCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssetUpdate(DomainModel):
    symbol: str | None = None
    venue: str | None = None
    description: str | None = None


class TimeframeCreate(DomainModel):
    name: str
    interval: str
    description: str | None = None


class Timeframe(TimeframeCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TimeframeUpdate(DomainModel):
    name: str | None = None
    interval: str | None = None
    description: str | None = None


class DatasetCreate(DomainModel):
    asset_id: str
    timeframe_id: str
    name: str
    description: str | None = None


class Dataset(DatasetCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetUpdate(DomainModel):
    asset_id: str | None = None
    timeframe_id: str | None = None
    name: str | None = None
    description: str | None = None


class FeatureCreate(DomainModel):
    dataset_id: str
    name: str
    values: dict[str, float] = Field(default_factory=dict)
    description: str | None = None


class Feature(FeatureCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeatureUpdate(DomainModel):
    dataset_id: str | None = None
    name: str | None = None
    values: dict[str, float] | None = None
    description: str | None = None


class ExperimentStatus(StrEnum):
    DRAFT = "Draft"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ExperimentCreate(DomainModel):
    dataset_id: str
    name: str
    hypothesis: str
    feature_id: str | None = None
    notes: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class Experiment(ExperimentCreate):
    id: str
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExperimentUpdate(DomainModel):
    dataset_id: str | None = None
    name: str | None = None
    hypothesis: str | None = None
    feature_id: str | None = None
    notes: str | None = None
    metrics: dict[str, float] | None = None
    status: ExperimentStatus | None = None


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
