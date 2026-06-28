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
    latest_candle_timestamp: datetime | None = None
    candle_count: int = 0
    last_ingestion_status: str | None = None
    last_ingestion_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetUpdate(DomainModel):
    asset_id: str | None = None
    timeframe_id: str | None = None
    name: str | None = None
    description: str | None = None


class Candle(DomainModel):
    id: str
    dataset_id: str
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CandleBackfillRequest(DomainModel):
    start_time: datetime | None = None
    end_time: datetime | None = None


class CandleBackfillResult(DomainModel):
    dataset_id: str
    inserted: int
    updated: int
    total_candles: int
    latest_candle_timestamp: datetime | None = None
    status: str


class FeatureComputeRequest(DomainModel):
    feature_names: list[str] | None = None


class FeatureSnapshot(DomainModel):
    id: str
    dataset_id: str
    timestamp: datetime
    feature_name: str
    numeric_value: float
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeatureSummaryItem(DomainModel):
    feature_name: str
    snapshot_count: int
    latest_timestamp: datetime | None = None
    latest_value: float | None = None


class FeatureSummary(DomainModel):
    dataset_id: str
    total_snapshots: int
    latest_timestamp: datetime | None = None
    features: list[FeatureSummaryItem] = Field(default_factory=list)


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestionJobType(StrEnum):
    CANDLE_BACKFILL = "candle_backfill"
    FEATURE_COMPUTE = "feature_compute"


class IngestionJob(DomainModel):
    id: str
    dataset_id: str
    job_type: IngestionJobType = IngestionJobType.CANDLE_BACKFILL
    status: IngestionJobStatus
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    candles_written: int = 0
    feature_snapshots_written: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
