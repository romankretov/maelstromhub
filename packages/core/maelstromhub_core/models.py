from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

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
    id: UUID
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
    id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TimeframeUpdate(DomainModel):
    name: str | None = None
    interval: str | None = None
    description: str | None = None


class DatasetCreate(DomainModel):
    asset_id: UUID
    timeframe_id: UUID
    name: str
    description: str | None = None


class Dataset(DatasetCreate):
    id: UUID
    latest_candle_timestamp: datetime | None = None
    candle_count: int = 0
    last_ingestion_status: str | None = None
    last_ingestion_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetUpdate(DomainModel):
    asset_id: UUID | None = None
    timeframe_id: UUID | None = None
    name: str | None = None
    description: str | None = None


class Candle(DomainModel):
    id: UUID
    dataset_id: UUID
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
    dataset_id: UUID
    inserted: int
    updated: int
    total_candles: int
    latest_candle_timestamp: datetime | None = None
    status: str


class FeatureComputeRequest(DomainModel):
    feature_names: list[str] | None = None


class FeatureSnapshot(DomainModel):
    id: UUID
    dataset_id: UUID
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
    dataset_id: UUID
    total_snapshots: int
    latest_timestamp: datetime | None = None
    features: list[FeatureSummaryItem] = Field(default_factory=list)


class TrendRegime(StrEnum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"


class VolatilityRegime(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class LiquidityRegime(StrEnum):
    NORMAL = "NORMAL"
    THIN = "THIN"


class RiskRegime(StrEnum):
    NORMAL = "NORMAL"
    STRESSED = "STRESSED"


class MarketRegimeSnapshot(DomainModel):
    id: UUID
    dataset_id: UUID
    timestamp: datetime
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    liquidity_regime: LiquidityRegime
    risk_regime: RiskRegime
    regime_label: str
    confidence: float
    explanation: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RegimeComputationResult(DomainModel):
    dataset_id: UUID
    snapshots_written: int
    current_regime: MarketRegimeSnapshot | None = None


class MarketIntelligence(DomainModel):
    dataset_id: UUID
    regime: MarketRegimeSnapshot | None = None


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestionJobType(StrEnum):
    CANDLE_BACKFILL = "candle_backfill"
    FEATURE_COMPUTE = "feature_compute"


class IngestionJob(DomainModel):
    id: UUID
    dataset_id: UUID
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
    dataset_id: UUID
    name: str
    values: dict[str, float] = Field(default_factory=dict)
    description: str | None = None


class Feature(FeatureCreate):
    id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeatureUpdate(DomainModel):
    dataset_id: UUID | None = None
    name: str | None = None
    values: dict[str, float] | None = None
    description: str | None = None


class ExperimentStatus(StrEnum):
    DRAFT = "Draft"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ExperimentCreate(DomainModel):
    dataset_id: UUID
    name: str
    hypothesis: str
    feature_id: UUID | None = None
    notes: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class Experiment(ExperimentCreate):
    id: UUID
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExperimentUpdate(DomainModel):
    dataset_id: UUID | None = None
    name: str | None = None
    hypothesis: str | None = None
    feature_id: UUID | None = None
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
    id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyCreate(DomainModel):
    name: str
    source_idea_id: UUID | None = None
    description: str


class Strategy(StrategyCreate):
    id: UUID
    status: StrategyStatus = StrategyStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyParameterValue(StrEnum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"


StrategyParameters = dict[str, int | float | str | bool | None]
StrategyParameterGrid = dict[str, list[int | float | str | bool | None]]


class StrategyTemplate(DomainModel):
    id: UUID
    name: str
    description: str
    required_features: list[str] = Field(default_factory=list)
    parameters: dict[str, str] = Field(default_factory=dict)
    default_parameters: StrategyParameters = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyVersionCreate(DomainModel):
    template_id: UUID
    dataset_id: UUID
    parameters: StrategyParameters = Field(default_factory=dict)
    allowed_regimes: list[str] | None = None


class StrategyVersion(StrategyVersionCreate):
    id: UUID
    strategy_id: UUID
    version_number: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SignalSide(StrEnum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class Signal(DomainModel):
    id: UUID
    strategy_version_id: UUID
    strategy_id: UUID
    dataset_id: UUID
    timestamp: datetime
    symbol: str
    side: SignalSide
    confidence: float
    reason: str
    suggested_size: float
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SignalRunResult(DomainModel):
    strategy_version_id: UUID
    signals_written: int
    total_signals: int


class BacktestStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BacktestRunCreate(DomainModel):
    starting_balance: float = 10_000.0
    fee_bps: float = 5.0
    slippage_bps: float = 2.0


class BacktestMetrics(DomainModel):
    total_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    trade_count: int = 0
    profit_factor: float = 0.0


class BacktestTrade(DomainModel):
    id: UUID
    backtest_run_id: UUID
    timestamp: datetime
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    fees: float
    reason: str


class EquityCurveSnapshot(DomainModel):
    id: UUID
    backtest_run_id: UUID
    timestamp: datetime
    equity: float
    drawdown: float


class BacktestRun(DomainModel):
    id: UUID
    strategy_version_id: UUID
    dataset_id: UUID
    status: BacktestStatus
    starting_balance: float
    fee_bps: float
    slippage_bps: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    metrics: dict[str, object] = Field(default_factory=dict)


class BacktestRunDetail(BacktestRun):
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[EquityCurveSnapshot] = Field(default_factory=list)


class BacktestVerdict(StrEnum):
    READY = "Ready"
    REVIEW = "Review"
    BLOCKED = "Blocked"


class BacktestEvaluation(DomainModel):
    verdict: BacktestVerdict
    risk_adjusted_score: float
    reasons: list[str] = Field(default_factory=list)
    thresholds: dict[str, float | int] = Field(default_factory=dict)


class StrategyPromotionResult(DomainModel):
    strategy: Strategy
    promoted: bool
    from_status: StrategyStatus
    to_status: StrategyStatus
    reasons: list[str] = Field(default_factory=list)
    backtest_run: BacktestRun | None = None
    evaluation: BacktestEvaluation | None = None


class WorkspaceRange(StrEnum):
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"
    DAYS_180 = "180d"
    YEAR_1 = "1y"


class WorkspaceLoadMarketRequest(DomainModel):
    symbol: str
    timeframe: str
    range: WorkspaceRange


class WorkspaceNoteCreate(DomainModel):
    symbol: str
    timeframe: str
    title: str
    body: str


class WorkspaceNoteUpdate(DomainModel):
    title: str | None = None
    body: str | None = None


class WorkspaceNote(WorkspaceNoteCreate):
    id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkspaceRunBacktestRequest(WorkspaceLoadMarketRequest):
    template_id: UUID
    parameters: StrategyParameters = Field(default_factory=dict)
    starting_balance: float = 10_000.0
    fee_bps: float = 5.0
    slippage_bps: float = 2.0
    allowed_regimes: list[str] | None = None


class WorkspaceOptimiseRequest(WorkspaceLoadMarketRequest):
    template_id: UUID
    parameter_grid: StrategyParameterGrid
    starting_balance: float = 10_000.0
    fee_bps: float = 5.0
    slippage_bps: float = 2.0
    allowed_regimes: list[str] | None = None


class WorkspaceMarketMetadata(DomainModel):
    symbol: str
    provider: str = "hyperliquid"
    timeframe: str
    range: WorkspaceRange
    asset_id: UUID | None = None


class WorkspaceCandleSummary(DomainModel):
    total_candles: int = 0
    first_candle_timestamp: datetime | None = None
    latest_candle_timestamp: datetime | None = None


class WorkspaceDataHealth(DomainModel):
    status: str
    detail: str
    last_ingestion_status: str | None = None
    queued_jobs: int = 0


class WorkspaceState(DomainModel):
    market: WorkspaceMarketMetadata
    dataset_id: UUID | None = None
    candle_summary: WorkspaceCandleSummary
    latest_candles: list[Candle] = Field(default_factory=list)
    feature_summary: FeatureSummary | None = None
    current_regime: MarketRegimeSnapshot | None = None
    available_strategy_templates: list[StrategyTemplate] = Field(default_factory=list)
    latest_backtests: list[BacktestRun] = Field(default_factory=list)
    data_health: WorkspaceDataHealth


class WorkspaceBacktestResult(DomainModel):
    workspace_state: WorkspaceState
    backtest: BacktestRunDetail
    evaluation: BacktestEvaluation
    signals_written: int
    total_signals: int


class WorkspaceOptimisationCandidate(DomainModel):
    rank: int
    parameters: StrategyParameters
    backtest: BacktestRun
    evaluation: BacktestEvaluation
    signals_written: int
    total_signals: int


class WorkspaceOptimisationResult(DomainModel):
    workspace_state: WorkspaceState
    total_combinations: int
    results: list[WorkspaceOptimisationCandidate] = Field(default_factory=list)


class PaperAccountStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class PaperDeploymentStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class PaperAccountCreate(DomainModel):
    name: str
    starting_balance: float = 10_000.0


class PaperAccount(DomainModel):
    id: UUID
    name: str
    starting_balance: float
    cash_balance: float
    equity: float
    status: PaperAccountStatus = PaperAccountStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaperDeploymentCreate(DomainModel):
    strategy_id: UUID
    strategy_version_id: UUID
    paper_account_id: UUID


class PaperTrade(DomainModel):
    id: UUID
    deployment_id: UUID
    timestamp: datetime
    symbol: str
    side: str
    price: float
    quantity: float
    fees: float
    pnl: float
    reason: str


class PaperPosition(DomainModel):
    id: UUID
    deployment_id: UUID
    symbol: str
    quantity: float
    average_entry_price: float
    unrealized_pnl: float
    realized_pnl: float


class PaperDeployment(DomainModel):
    id: UUID
    strategy_id: UUID
    strategy_version_id: UUID
    dataset_id: UUID
    paper_account_id: UUID
    status: PaperDeploymentStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stopped_at: datetime | None = None
    last_processed_at: datetime | None = None
    account: PaperAccount | None = None
    positions: list[PaperPosition] = Field(default_factory=list)
    trades: list[PaperTrade] = Field(default_factory=list)


class PaperStepResult(DomainModel):
    deployment: PaperDeployment
    advanced: bool
    message: str


class AuditEvent(DomainModel):
    id: UUID
    actor: str
    action: str
    subject: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchRun(DomainModel):
    id: UUID
    name: str
    status: ResearchRunStatus = ResearchRunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
