"""add backtests

Revision ID: 0007_add_backtests
Revises: 0006_add_strategy_sdk
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_add_backtests"
down_revision: str | None = "0006_add_strategy_sdk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("strategy_version_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("starting_balance", sa.Numeric(24, 10), nullable=False),
        sa.Column("fee_bps", sa.Numeric(12, 6), nullable=False),
        sa.Column("slippage_bps", sa.Numeric(12, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("backtest_run_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=80), nullable=False),
        sa.Column("side", sa.String(length=20), nullable=False),
        sa.Column("entry_price", sa.Numeric(24, 10), nullable=False),
        sa.Column("exit_price", sa.Numeric(24, 10), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 10), nullable=False),
        sa.Column("pnl", sa.Numeric(24, 10), nullable=False),
        sa.Column("fees", sa.Numeric(24, 10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["backtest_run_id"], ["backtest_runs.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "equity_curve_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("backtest_run_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(24, 10), nullable=False),
        sa.Column("drawdown", sa.Numeric(12, 8), nullable=False),
        sa.ForeignKeyConstraint(["backtest_run_id"], ["backtest_runs.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("equity_curve_snapshots")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_runs")
