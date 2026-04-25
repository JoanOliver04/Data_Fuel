"""ORM model for vehicle profiles."""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class VehicleProfileORM(Base):
    """Stores user-defined vehicle profiles for personalised cost calculation."""

    __tablename__ = "vehicle_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    fuel_consumption_per_100km: Mapped[float] = mapped_column(Float, nullable=False)
    tank_capacity_litres: Mapped[float] = mapped_column(Float, nullable=False)
    # Pre-computed reference K value (€/km) stored for display and fallback.
    km_cost_per_km: Mapped[float] = mapped_column(Float, nullable=False)
    # "urban" | "mixed" | "highway"
    driving_style: Mapped[str] = mapped_column(String(10), nullable=False, default="mixed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
