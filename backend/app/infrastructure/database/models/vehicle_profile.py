"""ORM model for vehicle profiles."""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class VehicleProfileORM(Base):
    """Stores user-defined vehicle profiles for personalised cost calculation.

    Three consumption values are stored so K can be selected dynamically from
    the driving distance to each station (see ``select_consumption_mode``).
    """

    __tablename__ = "vehicle_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    fuel_consumption_urban: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_consumption_mixed: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_consumption_highway: Mapped[float] = mapped_column(Float, nullable=False)
    tank_capacity_litres: Mapped[float] = mapped_column(Float, nullable=False)
    # Pre-computed reference K value (€/km) using mixed consumption — kept for
    # display fallback when no live price is available.
    km_cost_per_km: Mapped[float] = mapped_column(Float, nullable=False)
    # "urban" | "mixed" | "highway" — user's preferred default for display.
    driving_style: Mapped[str] = mapped_column(String(10), nullable=False, default="mixed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
