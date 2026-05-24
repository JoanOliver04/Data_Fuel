"""add training_runs table

Revision ID: 0002_add_training_runs
Revises: 0001_split_vehicle_consumption
Create Date: 2026-05-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_training_runs"
down_revision: str | None = "0001_split_vehicle_consumption"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the append-only retraining-run history table.

    Idempotent: the app runs ``Base.metadata.create_all`` before
    ``alembic upgrade head`` (see ``app.core.lifespan``), so on a fresh DB this
    table already exists and we must not recreate it. We only create it for
    legacy databases stamped below this revision that predate the model.
    """
    bind = op.get_bind()
    if "training_runs" in sa.inspect(bind).get_table_names():
        return

    op.create_table(
        "training_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=True),
        sa.Column("dataset_rows", sa.Integer(), nullable=True),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("r2", sa.Float(), nullable=True),
        sa.Column("r2_oob", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_training_runs_started_at", "training_runs", ["started_at"])


def downgrade() -> None:
    """Drop the retraining-run history table (if present)."""
    bind = op.get_bind()
    if "training_runs" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_training_runs_started_at", table_name="training_runs")
    op.drop_table("training_runs")
