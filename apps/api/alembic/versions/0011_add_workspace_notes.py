"""add workspace notes

Revision ID: 0011_add_workspace_notes
Revises: 0010_repair_uuid_columns
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_add_workspace_notes"
down_revision: str | None = "0010_repair_uuid_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("symbol", sa.String(length=40), nullable=False),
        sa.Column("timeframe", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_notes_symbol_timeframe", "workspace_notes", ["symbol", "timeframe"])


def downgrade() -> None:
    op.drop_index("ix_workspace_notes_symbol_timeframe", table_name="workspace_notes")
    op.drop_table("workspace_notes")
