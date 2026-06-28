from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, Numeric, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IdeaORM(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_idea_id: Mapped[str | None] = mapped_column(
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


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timeframe_id: Mapped[str] = mapped_column(ForeignKey("timeframes.id", ondelete="RESTRICT"), nullable=False)
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


class CandleORM(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("dataset_id", "opened_at", name="uq_candles_dataset_opened_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
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


class FeatureORM(Base):
    __tablename__ = "features"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    feature_id: Mapped[str | None] = mapped_column(ForeignKey("features.id", ondelete="SET NULL"), nullable=True)
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
