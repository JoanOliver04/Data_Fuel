"""ORM model for delivered notifications (append-only history)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class NotificationORM(Base):
    """One delivered notification. Append-only — never mutated after insert.

    ``alert_id`` is intentionally a plain nullable column (no FK) so deleting an
    alert keeps its notification history, and summary notifications without a
    single owning alert remain valid.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_identifier: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="deterministic")
    # Dedup signature (alert + rounded trigger state) — see the dispatcher.
    dedup_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_notifications_user_created", "user_identifier", "created_at"),
        Index("ix_notifications_dedup_created", "dedup_key", "created_at"),
    )
