"""add feature snapshots

Revision ID: 0005_add_feature_snapshots
Revises: 0004_add_ingestion_jobs
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_feature_snapshots"
down_revision: str | None = "0004_add_ingestion_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ingestion_jobs", sa.Column("job_type", sa.String(length=40), nullable=False, server_default="candle_backfill"))
    op.add_column("ingestion_jobs", sa.Column("feature_snapshots_written", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("ingestion_jobs", "job_type", server_default=None)
    op.alter_column("ingestion_jobs", "feature_snapshots_written", server_default=None)

    op.create_table(
        "feature_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_name", sa.String(length=120), nullable=False),
        sa.Column("numeric_value", sa.Numeric(24, 10), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "timestamp", "feature_name", name="uq_feature_snapshots_dataset_timestamp_name"),
    )


def downgrade() -> None:
    op.drop_table("feature_snapshots")
    op.drop_column("ingestion_jobs", "feature_snapshots_written")
    op.drop_column("ingestion_jobs", "job_type")
