"""Integration tests for app.services.historical_features_service.

These exercise the live SQL aggregates against an in-memory SQLite fixture
seeded with three days of multi-station prices across two municipios in the
same comarca.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database import session as db_session
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM
from app.services.historical_features_service import (
    comarca_mean_price,
    municipio_mean_price,
    municipio_mean_price_window,
    municipios_in_comarca,
)

_BASE_DATE = date(2026, 5, 1)
_BASE_DT = datetime(2026, 5, 1, 12, 0)


def _make_stations() -> list[StationORM]:
    """Two stations in Valencia (same comarca: Horta de València), one in Alzira."""
    return [
        StationORM(
            id=1,
            brand="Repsol",
            address="C/ Test 1",
            locality="Valencia",
            municipality="Valencia",
            province="Valencia",
            postal_code="46001",
            latitude=39.4697,
            longitude=-0.3774,
            schedule="L-D",
        ),
        StationORM(
            id=2,
            brand="Cepsa",
            address="C/ Test 2",
            locality="Valencia",
            municipality="Valencia",
            province="Valencia",
            postal_code="46002",
            latitude=39.47,
            longitude=-0.38,
            schedule="L-D",
        ),
        StationORM(
            id=3,
            brand="BP",
            address="C/ Test 3",
            locality="Alzira",
            municipality="Alzira",
            province="Valencia",
            postal_code="46600",
            latitude=39.1496,
            longitude=-0.4373,
            schedule="L-D",
        ),
    ]


def _make_prices() -> list[PriceHistoryORM]:
    """Three days of 95-octane prices, deterministic and easy to average."""
    prices = []
    # Day 0 (May 1): Valencia stations 1.500 & 1.700 (avg 1.600); Alzira 1.400.
    # Day 1 (May 2): Valencia 1.510 & 1.710 (avg 1.610);          Alzira 1.410.
    # Day 2 (May 3): Valencia 1.520 & 1.720 (avg 1.620);          Alzira 1.420.
    for day_offset in range(3):
        dt = _BASE_DT + timedelta(days=day_offset)
        prices.extend([
            PriceHistoryORM(
                station_id=1,
                fuel_type=FuelType.GASOLINA_95,
                price=round(1.500 + day_offset * 0.010, 3),
                recorded_at=dt,
            ),
            PriceHistoryORM(
                station_id=2,
                fuel_type=FuelType.GASOLINA_95,
                price=round(1.700 + day_offset * 0.010, 3),
                recorded_at=dt,
            ),
            PriceHistoryORM(
                station_id=3,
                fuel_type=FuelType.GASOLINA_95,
                price=round(1.400 + day_offset * 0.010, 3),
                recorded_at=dt,
            ),
        ])
    return prices


@pytest.fixture
async def populated(engine: AsyncEngine) -> AsyncSession:
    """Seed the in-memory DB and yield a session bound to it."""
    factory = db_session.get_session_factory()
    async with factory() as setup:
        setup.add_all(_make_stations())
        await setup.flush()
        setup.add_all(_make_prices())
        await setup.commit()
    async with factory() as session:
        yield session


# ── municipios_in_comarca (static JSON lookup) ────────────────────────────────


def test_municipios_in_comarca_returns_valencia_for_horta() -> None:
    municipios_in_comarca.cache_clear()
    munis = municipios_in_comarca("Horta de València")
    assert "Valencia" in munis


def test_municipios_in_comarca_unknown_returns_empty() -> None:
    municipios_in_comarca.cache_clear()
    assert municipios_in_comarca("Comarca Inexistente") == ()


# ── municipio_mean_price ──────────────────────────────────────────────────────


async def test_municipio_mean_price_averages_same_day_records(
    populated: AsyncSession,
) -> None:
    avg = await municipio_mean_price(
        populated, "Valencia", FuelType.GASOLINA_95, _BASE_DATE
    )
    # Day 0 Valencia: (1.500 + 1.700) / 2 = 1.600
    assert avg == pytest.approx(1.600, abs=0.001)


async def test_municipio_mean_price_returns_none_for_missing_day(
    populated: AsyncSession,
) -> None:
    far_future = _BASE_DATE + timedelta(days=365)
    avg = await municipio_mean_price(
        populated, "Valencia", FuelType.GASOLINA_95, far_future
    )
    assert avg is None


async def test_municipio_mean_price_isolates_by_municipio(
    populated: AsyncSession,
) -> None:
    # Alzira day 0 has a single station at 1.400 €/L.
    avg = await municipio_mean_price(
        populated, "Alzira", FuelType.GASOLINA_95, _BASE_DATE
    )
    assert avg == pytest.approx(1.400, abs=0.001)


# ── comarca_mean_price ────────────────────────────────────────────────────────


async def test_comarca_mean_price_aggregates_member_municipios(
    populated: AsyncSession,
) -> None:
    avg = await comarca_mean_price(
        populated, "Horta de València", FuelType.GASOLINA_95, _BASE_DATE
    )
    # Horta de València → maps to Valencia only in the fixture's price set.
    # Both stations 1 & 2 belong to it; (1.500 + 1.700) / 2 = 1.600.
    assert avg == pytest.approx(1.600, abs=0.001)


async def test_comarca_mean_price_unknown_comarca_returns_none(
    populated: AsyncSession,
) -> None:
    avg = await comarca_mean_price(
        populated, "Comarca Inexistente", FuelType.GASOLINA_95, _BASE_DATE
    )
    assert avg is None


# ── municipio_mean_price_window ───────────────────────────────────────────────


async def test_municipio_mean_price_window_averages_across_days(
    populated: AsyncSession,
) -> None:
    # 3-day window ending after May 3 covers all three days for Valencia.
    end = _BASE_DATE + timedelta(days=3)
    avg = await municipio_mean_price_window(
        populated, "Valencia", FuelType.GASOLINA_95, end, days=3
    )
    # Valencia per-day means: 1.600, 1.610, 1.620 → grand mean of the six
    # individual records: (1.500 + 1.700 + 1.510 + 1.710 + 1.520 + 1.720) / 6 = 1.610.
    assert avg == pytest.approx(1.610, abs=0.001)


async def test_municipio_mean_price_window_returns_none_outside_data(
    populated: AsyncSession,
) -> None:
    far_past = _BASE_DATE - timedelta(days=400)
    avg = await municipio_mean_price_window(
        populated, "Valencia", FuelType.GASOLINA_95, far_past, days=30
    )
    assert avg is None
