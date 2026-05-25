"""add analytics index on price_history(fuel_type, recorded_at)

Revision ID: 0004_analytics_indexes
Revises: 0003_add_alerts
Create Date: 2026-05-25

The analytics trend/comarca/brand queries filter price_history by fuel_type +
time window without a station_id. The existing composite index leads with
station_id, so it cannot serve those scans efficiently. This adds a covering
leading-column index. Portable across SQLite and PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_analytics_indexes"
down_revision: str | None = "0003_add_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_price_history_fuel_time"


def upgrade() -> None:
    """Create the (fuel_type, recorded_at) index if missing. Idempotent."""
    bind = op.get_bind()
    existing = {ix["name"] for ix in sa.inspect(bind).get_indexes("price_history")}
    if _INDEX not in existing:
        op.create_index(_INDEX, "price_history", ["fuel_type", "recorded_at"])


def downgrade() -> None:
    bind = op.get_bind()
    existing = {ix["name"] for ix in sa.inspect(bind).get_indexes("price_history")}
    if _INDEX in existing:
        op.drop_index(_INDEX, table_name="price_history")
