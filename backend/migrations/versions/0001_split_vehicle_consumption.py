"""split vehicle_profiles.fuel_consumption_per_100km into urban/mixed/highway

Revision ID: 0001_split_vehicle_consumption
Revises:
Create Date: 2026-04-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_split_vehicle_consumption"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add three per-band consumption columns and drop the legacy single one.

    On existing rows the legacy value is copied into all three new columns so
    saved profiles remain functional until the user edits them.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("vehicle_profiles")}

    with op.batch_alter_table("vehicle_profiles") as batch_op:
        if "fuel_consumption_urban" not in existing_cols:
            batch_op.add_column(
                sa.Column("fuel_consumption_urban", sa.Float(), nullable=True)
            )
        if "fuel_consumption_mixed" not in existing_cols:
            batch_op.add_column(
                sa.Column("fuel_consumption_mixed", sa.Float(), nullable=True)
            )
        if "fuel_consumption_highway" not in existing_cols:
            batch_op.add_column(
                sa.Column("fuel_consumption_highway", sa.Float(), nullable=True)
            )

    if "fuel_consumption_per_100km" in existing_cols:
        op.execute(
            sa.text(
                "UPDATE vehicle_profiles SET "
                "fuel_consumption_urban = COALESCE(fuel_consumption_urban, fuel_consumption_per_100km), "
                "fuel_consumption_mixed = COALESCE(fuel_consumption_mixed, fuel_consumption_per_100km), "
                "fuel_consumption_highway = COALESCE(fuel_consumption_highway, fuel_consumption_per_100km)"
            )
        )

    # Backfill any rows that had no legacy value either (defensive default).
    op.execute(
        sa.text(
            "UPDATE vehicle_profiles SET "
            "fuel_consumption_urban = COALESCE(fuel_consumption_urban, 7.0), "
            "fuel_consumption_mixed = COALESCE(fuel_consumption_mixed, 6.5), "
            "fuel_consumption_highway = COALESCE(fuel_consumption_highway, 5.5)"
        )
    )

    with op.batch_alter_table("vehicle_profiles") as batch_op:
        batch_op.alter_column("fuel_consumption_urban", existing_type=sa.Float(), nullable=False)
        batch_op.alter_column("fuel_consumption_mixed", existing_type=sa.Float(), nullable=False)
        batch_op.alter_column("fuel_consumption_highway", existing_type=sa.Float(), nullable=False)
        if "fuel_consumption_per_100km" in existing_cols:
            batch_op.drop_column("fuel_consumption_per_100km")


def downgrade() -> None:
    """Restore the single fuel_consumption_per_100km column from the mixed value."""
    with op.batch_alter_table("vehicle_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("fuel_consumption_per_100km", sa.Float(), nullable=True)
        )

    op.execute(
        sa.text(
            "UPDATE vehicle_profiles SET fuel_consumption_per_100km = fuel_consumption_mixed"
        )
    )

    with op.batch_alter_table("vehicle_profiles") as batch_op:
        batch_op.alter_column(
            "fuel_consumption_per_100km", existing_type=sa.Float(), nullable=False
        )
        batch_op.drop_column("fuel_consumption_highway")
        batch_op.drop_column("fuel_consumption_mixed")
        batch_op.drop_column("fuel_consumption_urban")
