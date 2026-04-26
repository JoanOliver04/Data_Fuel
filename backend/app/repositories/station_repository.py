"""SQLAlchemy repository for gas stations."""

import math
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.models.station import StationORM

# Safe chunk size for SQLite's 999-parameter limit: 999 // 16 cols ≈ 62.
_CHUNK = 60


def _price_column_for(
    fuel_type: FuelType,
) -> InstrumentedAttribute[Any] | None:
    """Map a fuel type to its denormalised current-price column on StationORM."""
    return {
        FuelType.GASOLINA_95: StationORM.price_gasoline_95_e5,
        FuelType.GASOLINA_95_E10: StationORM.price_gasoline_95_e10,
        FuelType.GASOLINA_98: StationORM.price_gasoline_98_e5,
        FuelType.GASOIL: StationORM.price_diesel_a,
        FuelType.GASOIL_PREMIUM: StationORM.price_diesel_premium,
    }.get(fuel_type)


class StationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, rows: list[dict[str, Any]]) -> int:
        """Bulk upsert stations. Skips created_at on conflict to preserve original value."""
        if not rows:
            return 0

        update_cols = {
            col.key
            for col in StationORM.__table__.columns
            if col.key not in ("id", "created_at")
        }
        total = 0
        for i in range(0, len(rows), _CHUNK):
            chunk = rows[i : i + _CHUNK]
            stmt = sqlite_insert(StationORM).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={k: getattr(stmt.excluded, k) for k in update_cols},
            )
            result = cast(CursorResult[Any], await self._session.execute(stmt))
            total += result.rowcount
        return total

    async def get_by_id(self, station_id: int) -> StationORM | None:
        return await self._session.get(StationORM, station_id)

    async def list_all(
        self,
        province: str | None = None,
        municipality: str | None = None,
    ) -> Sequence[StationORM]:
        q = select(StationORM)
        if province:
            q = q.where(StationORM.province.ilike(f"%{province}%"))
        if municipality:
            q = q.where(StationORM.municipality.ilike(f"%{municipality}%"))
        result = await self._session.execute(q)
        return result.scalars().all()

    async def find_candidates(
        self,
        fuel_type: FuelType,
        bbox: tuple[float, float, float, float] | None = None,
        radius_origin: tuple[float, float, float] | None = None,
    ) -> Sequence[StationORM]:
        """Return stations sellling ``fuel_type`` and inside an optional area.

        ``bbox`` is ``(south, north, west, east)``. When omitted but
        ``radius_origin=(lat, lon, max_km)`` is given, a bounding square that
        encloses the circle of radius ``max_km`` around the origin is applied
        instead — the haversine cut is later refined in ``rank_stations``.

        Pushing these filters into SQL avoids hydrating the entire stations
        table (~10k rows) on every recommendations call.
        """
        col = _price_column_for(fuel_type)
        if col is None:
            return []

        q = select(StationORM).where(col.is_not(None))

        if bbox is not None:
            south, north, west, east = bbox
            q = q.where(StationORM.latitude.between(south, north))
            q = q.where(StationORM.longitude.between(west, east))
        elif radius_origin is not None:
            lat, lon, r_km = radius_origin
            d_lat = r_km / 111.0
            # cos(lat) shrinks longitude degree length toward the poles. Clamp
            # to avoid a near-zero denominator at extreme latitudes.
            d_lon = r_km / (111.0 * max(0.01, math.cos(math.radians(lat))))
            q = q.where(StationORM.latitude.between(lat - d_lat, lat + d_lat))
            q = q.where(StationORM.longitude.between(lon - d_lon, lon + d_lon))

        result = await self._session.execute(q)
        return result.scalars().all()

    async def avg_price_for_fuel_type(self, fuel_type: FuelType) -> float | None:
        """Return the average current price across all stations for a given fuel type."""
        col = _price_column_for(fuel_type)
        if col is None:
            return None
        result = await self._session.execute(select(func.avg(col)))
        value = result.scalar_one_or_none()
        return float(value) if value is not None else None
