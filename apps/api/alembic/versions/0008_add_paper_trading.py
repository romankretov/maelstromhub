"""add paper trading

Revision ID: 0008_add_paper_trading
Revises: 0007_add_backtests
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_add_paper_trading"
down_revision: str | None = "0007_add_backtests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("starting_balance", sa.Numeric(24, 10), nullable=False),
        sa.Column("cash_balance", sa.Numeric(24, 10), nullable=False),
        sa.Column("equity", sa.Numeric(24, 10), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_deployments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("strategy_id", sa.String(length=36), nullable=False),
        sa.Column("strategy_version_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("paper_account_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "paper_trades",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("deployment_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=80), nullable=False),
        sa.Column("side", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Numeric(24, 10), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 10), nullable=False),
        sa.Column("fees", sa.Numeric(24, 10), nullable=False),
        sa.Column("pnl", sa.Numeric(24, 10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["deployment_id"], ["paper_deployments.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "paper_positions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("deployment_id", sa.String(length=36), nullable=False),
        sa.Column("symbol", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 10), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(24, 10), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(24, 10), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(24, 10), nullable=False),
        sa.ForeignKeyConstraint(["deployment_id"], ["paper_deployments.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("paper_positions")
    op.drop_table("paper_trades")
    op.drop_table("paper_deployments")
    op.drop_table("paper_accounts")
