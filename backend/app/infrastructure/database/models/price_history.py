"""ORM model for historical fuel prices (one row per station / fuel / observation)."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.station import StationORM


class PriceHistoryORM(Base):
    """Time-series of fuel prices, used both for current price and ML training."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
    )
    fuel_type: Mapped[FuelType] = mapped_column(String(32), nullable=False)

    # Numeric(5,3) → up to 99.999 €/L; precise enough for cent-level prices.
    price: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    station: Mapped["StationORM"] = relationship(back_populates="price_history")

    __table_args__ = (
        Index(
            "ix_price_history_station_fuel_time",
            "station_id",
            "fuel_type",
            "recorded_at",
        ),
    )
