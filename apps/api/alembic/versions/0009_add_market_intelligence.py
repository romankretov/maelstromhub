"""add market intelligence regimes

Revision ID: 0009_add_market_intelligence
Revises: 0008_add_paper_trading
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_add_market_intelligence"
down_revision: str | None = "0008_add_paper_trading"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("strategy_versions", sa.Column("allowed_regimes", sa.JSON(), nullable=True))
    op.create_table(
        "market_regime_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trend_regime", sa.String(length=40), nullable=False),
        sa.Column("volatility_regime", sa.String(length=40), nullable=False),
        sa.Column("liquidity_regime", sa.String(length=40), nullable=False),
        sa.Column("risk_regime", sa.String(length=40), nullable=False),
        sa.Column("regime_label", sa.String(length=120), nullable=False),
        sa.Column("confidence", sa.Numeric(10, 6), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "timestamp", name="uq_market_regimes_dataset_timestamp"),
    )


def downgrade() -> None:
    op.drop_table("market_regime_snapshots")
    op.drop_column("strategy_versions", "allowed_regimes")
