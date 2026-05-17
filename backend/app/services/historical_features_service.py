"""Runtime feature lookups that mirror the train-time aggregations.

These helpers query the same ``price_history`` ⨝ ``stations`` join that the
export pipeline uses, so the inference-time feature vector carries live
values for the highest-importance market-context features
(``precio_medio_municipio``, ``precio_vs_media_comarca``,
``precio_semana_anterior``, ``tendencia_ultimos_30_dias``).

When the database has no rows for the requested ``(municipio | comarca,
fuel_type, date)`` bucket each helper returns ``None``; callers are
expected to substitute a neutral default. This is intentional: the
recommendation endpoint must never block on data freshness, and a freshly
deployed environment is allowed to serve degraded-confidence predictions
until the next MITECO sync.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

_COMARCAS_PATH = (
    Path(__file__).resolve().parents[1] / "ml" / "data" / "comarcas_valencia.json"
)


@lru_cache(maxsize=1)
def _comarcas_map() -> dict[str, str]:
    """Cached ``municipio → comarca`` mapping loaded from the static JSON."""
    with _COMARCAS_PATH.open(encoding="utf-8") as fh:
        data: dict[str, str] = json.load(fh)
        return data


@lru_cache(maxsize=128)
def municipios_in_comarca(comarca: str) -> tuple[str, ...]:
    """Reverse lookup: tuple of municipios that map to ``comarca``."""
    return tuple(m for m, c in _comarcas_map().items() if c == comarca)


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, datetime.min.time())
    return start, start + timedelta(days=1)


async def municipio_mean_price(
    session: AsyncSession,
    municipio: str,
    fuel_type: FuelType,
    on_date: date,
) -> float | None:
    """Daily average price for ``(municipio, fuel_type)`` on ``on_date``."""
    start, end = _day_bounds(on_date)
    stmt = (
        select(func.avg(PriceHistoryORM.price))
        .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
        .where(
            StationORM.municipality == municipio,
            PriceHistoryORM.fuel_type == fuel_type.value,
            PriceHistoryORM.recorded_at >= start,
            PriceHistoryORM.recorded_at < end,
        )
    )
    value = (await session.execute(stmt)).scalar()
    return float(value) if value is not None else None


async def comarca_mean_price(
    session: AsyncSession,
    comarca: str,
    fuel_type: FuelType,
    on_date: date,
) -> float | None:
    """Daily average price across every municipio mapped to ``comarca``."""
    municipios = municipios_in_comarca(comarca)
    if not municipios:
        return None
    start, end = _day_bounds(on_date)
    stmt = (
        select(func.avg(PriceHistoryORM.price))
        .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
        .where(
            StationORM.municipality.in_(municipios),
            PriceHistoryORM.fuel_type == fuel_type.value,
            PriceHistoryORM.recorded_at >= start,
            PriceHistoryORM.recorded_at < end,
        )
    )
    value = (await session.execute(stmt)).scalar()
    return float(value) if value is not None else None


async def municipio_mean_price_window(
    session: AsyncSession,
    municipio: str,
    fuel_type: FuelType,
    end_date: date,
    days: int,
) -> float | None:
    """Average price across the last ``days`` ending at ``end_date`` (exclusive)."""
    end = datetime.combine(end_date, datetime.min.time())
    start = end - timedelta(days=days)
    stmt = (
        select(func.avg(PriceHistoryORM.price))
        .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
        .where(
            StationORM.municipality == municipio,
            PriceHistoryORM.fuel_type == fuel_type.value,
            PriceHistoryORM.recorded_at >= start,
            PriceHistoryORM.recorded_at < end,
        )
    )
    value = (await session.execute(stmt)).scalar()
    return float(value) if value is not None else None
