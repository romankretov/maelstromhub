from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Integer, Numeric, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IdeaORM(Base):
    __tablename__ = "ideas"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    strategies: Mapped[list["StrategyORM"]] = relationship(back_populates="source_idea")


class StrategyORM(Base):
    __tablename__ = "strategies"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_idea_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ideas.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    source_idea: Mapped[IdeaORM | None] = relationship(back_populates="strategies")
    versions: Mapped[list["StrategyVersionORM"]] = relationship(back_populates="strategy", passive_deletes=True)
    signals: Mapped[list["SignalORM"]] = relationship(back_populates="strategy", passive_deletes=True)


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class AssetORM(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    symbol: Mapped[str] = mapped_column(String(40), nullable=False)
    venue: Mapped[str] = mapped_column(String(80), nullable=False, default="hyperliquid")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    datasets: Mapped[list["DatasetORM"]] = relationship(back_populates="asset", passive_deletes=True)


class TimeframeORM(Base):
    __tablename__ = "timeframes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    interval: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    datasets: Mapped[list["DatasetORM"]] = relationship(back_populates="timeframe", passive_deletes=True)


class DatasetORM(Base):
    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timeframe_id: Mapped[UUID] = mapped_column(ForeignKey("timeframes.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_candle_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candle_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_ingestion_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    asset: Mapped[AssetORM] = relationship(back_populates="datasets")
    timeframe: Mapped[TimeframeORM] = relationship(back_populates="datasets")
    features: Mapped[list["FeatureORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    experiments: Mapped[list["ExperimentORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    candles: Mapped[list["CandleORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    ingestion_jobs: Mapped[list["IngestionJobORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    feature_snapshots: Mapped[list["FeatureSnapshotORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    regime_snapshots: Mapped[list["MarketRegimeSnapshotORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    strategy_versions: Mapped[list["StrategyVersionORM"]] = relationship(back_populates="dataset", passive_deletes=True)
    signals: Mapped[list["SignalORM"]] = relationship(back_populates="dataset", passive_deletes=True)


class CandleORM(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("dataset_id", "opened_at", name="uq_candles_dataset_opened_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    trade_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset: Mapped[DatasetORM] = relationship(back_populates="candles")


class IngestionJobORM(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(40), default="candle_backfill", nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candles_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_snapshots_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset: Mapped[DatasetORM] = relationship(back_populates="ingestion_jobs")


class FeatureSnapshotORM(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (UniqueConstraint("dataset_id", "timestamp", "feature_name", name="uq_feature_snapshots_dataset_timestamp_name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(120), nullable=False)
    numeric_value: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset: Mapped[DatasetORM] = relationship(back_populates="feature_snapshots")


class MarketRegimeSnapshotORM(Base):
    __tablename__ = "market_regime_snapshots"
    __table_args__ = (UniqueConstraint("dataset_id", "timestamp", name="uq_market_regimes_dataset_timestamp"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trend_regime: Mapped[str] = mapped_column(String(40), nullable=False)
    volatility_regime: Mapped[str] = mapped_column(String(40), nullable=False)
    liquidity_regime: Mapped[str] = mapped_column(String(40), nullable=False)
    risk_regime: Mapped[str] = mapped_column(String(40), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset: Mapped[DatasetORM] = relationship(back_populates="regime_snapshots")


class StrategyTemplateORM(Base):
    __tablename__ = "strategy_templates"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parameters: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    default_parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    versions: Mapped[list["StrategyVersionORM"]] = relationship(back_populates="template", passive_deletes=True)


class StrategyVersionORM(Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version_number", name="uq_strategy_versions_strategy_number"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[UUID] = mapped_column(ForeignKey("strategy_templates.id", ondelete="RESTRICT"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    allowed_regimes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    strategy: Mapped[StrategyORM] = relationship(back_populates="versions")
    template: Mapped[StrategyTemplateORM] = relationship(back_populates="versions")
    dataset: Mapped[DatasetORM] = relationship(back_populates="strategy_versions")
    signals: Mapped[list["SignalORM"]] = relationship(back_populates="strategy_version", passive_deletes=True)
    backtest_runs: Mapped[list["BacktestRunORM"]] = relationship(back_populates="strategy_version", passive_deletes=True)


class SignalORM(Base):
    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("strategy_version_id", "timestamp", name="uq_signals_version_timestamp"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    strategy_version_id: Mapped[UUID] = mapped_column(ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[UUID] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_size: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    strategy_version: Mapped[StrategyVersionORM] = relationship(back_populates="signals")
    strategy: Mapped[StrategyORM] = relationship(back_populates="signals")
    dataset: Mapped[DatasetORM] = relationship(back_populates="signals")


class BacktestRunORM(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    strategy_version_id: Mapped[UUID] = mapped_column(ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    starting_balance: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    fee_bps: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    slippage_bps: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    strategy_version: Mapped[StrategyVersionORM] = relationship(back_populates="backtest_runs")
    trades: Mapped[list["BacktestTradeORM"]] = relationship(back_populates="backtest_run", passive_deletes=True)
    equity_curve: Mapped[list["EquityCurveSnapshotORM"]] = relationship(back_populates="backtest_run", passive_deletes=True)


class PaperAccountORM(Base):
    __tablename__ = "paper_accounts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    starting_balance: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    cash_balance: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    equity: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    deployments: Mapped[list["PaperDeploymentORM"]] = relationship(back_populates="account", passive_deletes=True)


class PaperDeploymentORM(Base):
    __tablename__ = "paper_deployments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    strategy_version_id: Mapped[UUID] = mapped_column(ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    paper_account_id: Mapped[UUID] = mapped_column(ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[PaperAccountORM] = relationship(back_populates="deployments")
    trades: Mapped[list["PaperTradeORM"]] = relationship(back_populates="deployment", passive_deletes=True)
    positions: Mapped[list["PaperPositionORM"]] = relationship(back_populates="deployment", passive_deletes=True)


class PaperTradeORM(Base):
    __tablename__ = "paper_trades"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    deployment_id: Mapped[UUID] = mapped_column(ForeignKey("paper_deployments.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    fees: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    pnl: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    deployment: Mapped[PaperDeploymentORM] = relationship(back_populates="trades")


class PaperPositionORM(Base):
    __tablename__ = "paper_positions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    deployment_id: Mapped[UUID] = mapped_column(ForeignKey("paper_deployments.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    average_entry_price: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)

    deployment: Mapped[PaperDeploymentORM] = relationship(back_populates="positions")


class BacktestTradeORM(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    backtest_run_id: Mapped[UUID] = mapped_column(ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    exit_price: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    pnl: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    fees: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    backtest_run: Mapped[BacktestRunORM] = relationship(back_populates="trades")


class EquityCurveSnapshotORM(Base):
    __tablename__ = "equity_curve_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    backtest_run_id: Mapped[UUID] = mapped_column(ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    equity: Mapped[float] = mapped_column(Numeric(24, 10), nullable=False)
    drawdown: Mapped[float] = mapped_column(Numeric(12, 8), nullable=False)

    backtest_run: Mapped[BacktestRunORM] = relationship(back_populates="equity_curve")


class FeatureORM(Base):
    __tablename__ = "features"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    values: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset: Mapped[DatasetORM] = relationship(back_populates="features")
    experiments: Mapped[list["ExperimentORM"]] = relationship(back_populates="feature", passive_deletes=True)


class ExperimentORM(Base):
    __tablename__ = "experiments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    feature_id: Mapped[UUID | None] = mapped_column(ForeignKey("features.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset: Mapped[DatasetORM] = relationship(back_populates="experiments")
    feature: Mapped[FeatureORM | None] = relationship(back_populates="experiments")
