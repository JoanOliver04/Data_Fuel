"""add alerts and notifications tables

Revision ID: 0003_add_alerts
Revises: 0002_add_training_runs
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_alerts"
down_revision: str | None = "0002_add_training_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the alerts + notifications tables.

    Idempotent: the app runs ``Base.metadata.create_all`` before
    ``alembic upgrade head`` (see ``app.core.lifespan``), so on a fresh DB these
    tables already exist; we only create them for legacy DBs stamped below this
    revision.
    """
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "alerts" not in existing:
        op.create_table(
            "alerts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_identifier", sa.String(length=120), nullable=False),
            sa.Column("alert_type", sa.String(length=40), nullable=False),
            sa.Column("fuel_type", sa.String(length=30), nullable=False),
            sa.Column("station_id", sa.Integer(), nullable=True),
            sa.Column("brand", sa.String(length=120), nullable=True),
            sa.Column("threshold_price", sa.Numeric(6, 3), nullable=True),
            sa.Column("threshold_pct", sa.Float(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("radius_km", sa.Float(), nullable=False, server_default="10.0"),
            sa.Column("liters", sa.Float(), nullable=False, server_default="50.0"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="360"),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True),
                server_default=sa.func.now(), nullable=False,
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True),
                server_default=sa.func.now(), nullable=False,
            ),
        )
        op.create_index("ix_alerts_user_identifier", "alerts", ["user_identifier"])
        op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
        op.create_index("ix_alerts_station_id", "alerts", ["station_id"])
        op.create_index("ix_alerts_is_enabled", "alerts", ["is_enabled"])
        op.create_index("ix_alerts_user_enabled", "alerts", ["user_identifier", "is_enabled"])

    if "notifications" not in existing:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("alert_id", sa.Integer(), nullable=True),
            sa.Column("user_identifier", sa.String(length=120), nullable=False),
            sa.Column("alert_type", sa.String(length=40), nullable=False),
            sa.Column("channel", sa.String(length=20), nullable=False, server_default="in_app"),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("message", sa.String(length=1000), nullable=False),
            sa.Column(
                "source", sa.String(length=20), nullable=False, server_default="deterministic"
            ),
            sa.Column("dedup_key", sa.String(length=120), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True),
                server_default=sa.func.now(), nullable=False,
            ),
        )
        op.create_index("ix_notifications_alert_id", "notifications", ["alert_id"])
        op.create_index("ix_notifications_user_identifier", "notifications", ["user_identifier"])
        op.create_index("ix_notifications_dedup_key", "notifications", ["dedup_key"])
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
        op.create_index(
            "ix_notifications_user_created", "notifications", ["user_identifier", "created_at"]
        )
        op.create_index(
            "ix_notifications_dedup_created", "notifications", ["dedup_key", "created_at"]
        )


def downgrade() -> None:
    """Drop the alerts + notifications tables (if present)."""
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "notifications" in existing:
        op.drop_table("notifications")
    if "alerts" in existing:
        op.drop_table("alerts")
