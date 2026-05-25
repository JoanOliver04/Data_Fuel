"""Read-only SQL aggregations for analytics.

All queries are time-windowed and grouped in the database (never pulling raw
rows into Python) so payloads stay small and the frontend never aggregates.
Joins use the existing ``(station_id, fuel_type, recorded_at)`` index on
``price_history``. The repository returns small typed rows; services shape them
into DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Numeric, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.dialects import Granularity, time_bucket
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

# fuel_type value → current-price column on stations (denormalised snapshot)
_FUEL_COLUMN: dict[str, InstrumentedAttribute[Decimal | None]] = {
    "gasolina_95": StationORM.price_gasoline_95_e5,
    "gasolina_95_e10": StationORM.price_gasoline_95_e10,
    "gasolina_98": StationORM.price_gasoline_98_e5,
    "gasoil": StationORM.price_diesel_a,
    "gasoil_premium": StationORM.price_diesel_premium,
}


def fuel_column(fuel: str) -> InstrumentedAttribute[Decimal | None]:
    col = _FUEL_COLUMN.get(fuel)
    if col is None:
        raise ValueError(f"Unknown fuel_type: {fuel}")
    return col


@dataclass(frozen=True, slots=True)
class TrendRow:
    bucket: str
    avg: float
    min: float
    max: float
    count: int


@dataclass(frozen=True, slots=True)
class LabeledTrendRow:
    label: str
    bucket: str
    avg: float
    min: float
    max: float
    count: int


@dataclass(frozen=True, slots=True)
class GroupStatRow:
    key: str  # municipality or brand
    avg: float
    min: float
    max: float
    sample_count: int
    station_count: int


@dataclass(frozen=True, slots=True)
class HeatRow:
    station_id: int
    lat: float
    lon: float
    brand: str
    municipality: str
    price: float


def _f(value: Any) -> float:
    return float(value) if value is not None else 0.0


class AnalyticsRepository:
    """Aggregation queries over price_history ⨝ stations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_stations(self) -> int:
        return int((await self._session.execute(select(func.count(StationORM.id)))).scalar() or 0)

    async def count_observations(self) -> int:
        return int(
            (await self._session.execute(select(func.count(PriceHistoryORM.id)))).scalar() or 0
        )

    async def current_fuel_averages(self) -> dict[str, float]:
        """Average current (snapshot) price per fuel across stations with a price."""
        averages: dict[str, float] = {}
        for fuel, col in _FUEL_COLUMN.items():
            value = (await self._session.execute(select(func.avg(col)))).scalar()
            if value is not None:
                averages[fuel] = round(float(value), 3)
        return averages

    async def trend_rows(
        self, fuel: str, start: datetime, end: datetime, granularity: Granularity
    ) -> list[TrendRow]:
        bucket = time_bucket(PriceHistoryORM.recorded_at, granularity).label("bucket")
        stmt = (
            select(
                bucket,
                func.avg(PriceHistoryORM.price),
                func.min(PriceHistoryORM.price),
                func.max(PriceHistoryORM.price),
                func.count(),
            )
            .where(
                PriceHistoryORM.fuel_type == fuel,
                PriceHistoryORM.recorded_at >= start,
                PriceHistoryORM.recorded_at < end,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = (await self._session.execute(stmt)).all()
        return [TrendRow(str(r[0]), _f(r[1]), _f(r[2]), _f(r[3]), int(r[4])) for r in rows]

    async def trend_rows_by_brand(
        self, fuel: str, start: datetime, end: datetime, granularity: Granularity, brands: list[str]
    ) -> list[LabeledTrendRow]:
        bucket = time_bucket(PriceHistoryORM.recorded_at, granularity).label("bucket")
        stmt = (
            select(
                StationORM.brand,
                bucket,
                func.avg(PriceHistoryORM.price),
                func.min(PriceHistoryORM.price),
                func.max(PriceHistoryORM.price),
                func.count(),
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .where(
                PriceHistoryORM.fuel_type == fuel,
                PriceHistoryORM.recorded_at >= start,
                PriceHistoryORM.recorded_at < end,
                StationORM.brand.in_(brands),
            )
            .group_by(StationORM.brand, bucket)
            .order_by(StationORM.brand, bucket)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            LabeledTrendRow(str(r[0]), str(r[1]), _f(r[2]), _f(r[3]), _f(r[4]), int(r[5]))
            for r in rows
        ]

    async def trend_rows_by_municipality(
        self, fuel: str, start: datetime, end: datetime, granularity: Granularity
    ) -> list[LabeledTrendRow]:
        bucket = time_bucket(PriceHistoryORM.recorded_at, granularity).label("bucket")
        stmt = (
            select(
                StationORM.municipality,
                bucket,
                func.avg(PriceHistoryORM.price),
                func.min(PriceHistoryORM.price),
                func.max(PriceHistoryORM.price),
                func.count(),
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .where(
                PriceHistoryORM.fuel_type == fuel,
                PriceHistoryORM.recorded_at >= start,
                PriceHistoryORM.recorded_at < end,
            )
            .group_by(StationORM.municipality, bucket)
            .order_by(bucket)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            LabeledTrendRow(str(r[0]), str(r[1]), _f(r[2]), _f(r[3]), _f(r[4]), int(r[5]))
            for r in rows
        ]

    async def municipality_window_stats(
        self, fuel: str, start: datetime, end: datetime
    ) -> list[GroupStatRow]:
        stmt = (
            select(
                StationORM.municipality,
                func.avg(PriceHistoryORM.price),
                func.min(PriceHistoryORM.price),
                func.max(PriceHistoryORM.price),
                func.count(),
                func.count(func.distinct(PriceHistoryORM.station_id)),
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .where(
                PriceHistoryORM.fuel_type == fuel,
                PriceHistoryORM.recorded_at >= start,
                PriceHistoryORM.recorded_at < end,
            )
            .group_by(StationORM.municipality)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            GroupStatRow(str(r[0]), _f(r[1]), _f(r[2]), _f(r[3]), int(r[4]), int(r[5]))
            for r in rows
        ]

    async def brand_window_stats(
        self, fuel: str, start: datetime, end: datetime
    ) -> list[GroupStatRow]:
        stmt = (
            select(
                StationORM.brand,
                func.avg(PriceHistoryORM.price),
                func.min(PriceHistoryORM.price),
                func.max(PriceHistoryORM.price),
                func.count(),
                func.count(func.distinct(PriceHistoryORM.station_id)),
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .where(
                PriceHistoryORM.fuel_type == fuel,
                PriceHistoryORM.recorded_at >= start,
                PriceHistoryORM.recorded_at < end,
            )
            .group_by(StationORM.brand)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            GroupStatRow(str(r[0]), _f(r[1]), _f(r[2]), _f(r[3]), int(r[4]), int(r[5]))
            for r in rows
        ]

    async def heatmap_rows(
        self,
        fuel: str,
        *,
        north: float | None = None,
        south: float | None = None,
        east: float | None = None,
        west: float | None = None,
        limit: int = 2000,
    ) -> list[HeatRow]:
        col = fuel_column(fuel).cast(Numeric(5, 3))
        stmt = select(
            StationORM.id,
            StationORM.latitude,
            StationORM.longitude,
            StationORM.brand,
            StationORM.municipality,
            col,
        ).where(fuel_column(fuel).is_not(None))
        if None not in (north, south, east, west):
            stmt = stmt.where(
                StationORM.latitude <= north,
                StationORM.latitude >= south,
                StationORM.longitude <= east,
                StationORM.longitude >= west,
            )
        stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).all()
        return [
            HeatRow(int(r[0]), float(r[1]), float(r[2]), str(r[3]), str(r[4]), _f(r[5]))
            for r in rows
        ]
