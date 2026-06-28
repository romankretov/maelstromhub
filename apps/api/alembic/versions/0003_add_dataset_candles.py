"""add dataset candles

Revision ID: 0003_add_dataset_candles
Revises: 0002_create_research_tables
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_dataset_candles"
down_revision: str | None = "0002_create_research_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("latest_candle_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("datasets", sa.Column("candle_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("datasets", sa.Column("last_ingestion_status", sa.String(length=40), nullable=True))
    op.add_column("datasets", sa.Column("last_ingestion_error", sa.Text(), nullable=True))
    op.alter_column("datasets", "candle_count", server_default=None)

    op.create_table(
        "candles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(24, 10), nullable=False),
        sa.Column("high", sa.Numeric(24, 10), nullable=False),
        sa.Column("low", sa.Numeric(24, 10), nullable=False),
        sa.Column("close", sa.Numeric(24, 10), nullable=False),
        sa.Column("volume", sa.Numeric(24, 10), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "opened_at", name="uq_candles_dataset_opened_at"),
    )


def downgrade() -> None:
    op.drop_table("candles")
    op.drop_column("datasets", "last_ingestion_error")
    op.drop_column("datasets", "last_ingestion_status")
    op.drop_column("datasets", "candle_count")
    op.drop_column("datasets", "latest_candle_timestamp")
