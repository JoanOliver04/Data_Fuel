"""ORM model for user-defined alerts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AlertORM(Base):
    """A persistent, user-configured intelligent alert."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_identifier: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    fuel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    station_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    threshold_price: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    threshold_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_km: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    liters: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=360)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Batch evaluation scans enabled alerts per user; this composite index serves
    # both the scheduler sweep and the per-user listing endpoint.
    __table_args__ = (Index("ix_alerts_user_enabled", "user_identifier", "is_enabled"),)
