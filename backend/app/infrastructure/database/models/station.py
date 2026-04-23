"""ORM model for gas stations."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.price_history import PriceHistoryORM


class StationORM(Base):
    """Persistent representation of a MITECO gas station."""

    __tablename__ = "stations"

    # MITECO IDEESS as primary key (stable across syncs).
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)

    brand: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    locality: Mapped[str] = mapped_column(String(120), nullable=False)
    municipality: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    schedule: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    price_history: Mapped[list["PriceHistoryORM"]] = relationship(
        back_populates="station",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_stations_geo", "latitude", "longitude"),
    )
