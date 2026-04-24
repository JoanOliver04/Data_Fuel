"""Integration tests for GET /api/v1/stations/{station_id}/price-history/{fuel_type}."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM


def _station(station_id: int = 200) -> StationORM:
    return StationORM(
        id=station_id,
        brand="REPSOL",
        address="Calle Test 1",
        locality="Valencia",
        municipality="Valencia",
        province="Valencia",
        postal_code="46001",
        latitude=39.47,
        longitude=-0.376,
        schedule="L-D: 24H",
        price_diesel_a=Decimal("1.489"),
    )


def _price_rows(station_id: int, n: int) -> list[PriceHistoryORM]:
    """Recent rows — within the default 30-day look-back window."""
    now = datetime.now(tz=UTC)
    return [
        PriceHistoryORM(
            station_id=station_id,
            fuel_type="diesel_a",
            price=Decimal(str(round(1.489 + (i % 5) * 0.01, 3))),
            recorded_at=now - timedelta(hours=(n - i) * 6),
        )
        for i in range(n)
    ]


@pytest.fixture
async def seeded_station(db: AsyncSession) -> None:
    station = _station()
    db.add(station)
    await db.flush()
    db.add_all(_price_rows(station.id, 5))
    await db.commit()


@pytest.fixture
async def empty_station(db: AsyncSession) -> None:
    station = _station(station_id=201)
    db.add(station)
    await db.commit()


# ── happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_200_with_price_points(api_client: AsyncClient, seeded_station: None) -> None:
    resp = await api_client.get("/api/v1/stations/200/price-history/diesel_a")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 5
    assert all("recorded_at" in p and "price" in p for p in body)


@pytest.mark.asyncio
async def test_price_points_sorted_ascending(api_client: AsyncClient, seeded_station: None) -> None:
    resp = await api_client.get("/api/v1/stations/200/price-history/diesel_a")
    timestamps = [p["recorded_at"] for p in resp.json()]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_empty_history_returns_empty_list(
    api_client: AsyncClient, empty_station: None
) -> None:
    resp = await api_client.get("/api/v1/stations/201/price-history/diesel_a")
    assert resp.status_code == 200
    assert resp.json() == []


# ── error cases ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_station_not_found_returns_404(api_client: AsyncClient, engine: object) -> None:
    resp = await api_client.get("/api/v1/stations/99999/price-history/diesel_a")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_fuel_type_returns_422(api_client: AsyncClient, engine: object) -> None:
    resp = await api_client.get("/api/v1/stations/200/price-history/not_a_fuel")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_days_param_filters_old_records(
    api_client: AsyncClient, db: AsyncSession
) -> None:
    station = _station(station_id=202)
    db.add(station)
    await db.flush()
    now = datetime.now(tz=UTC)
    db.add(
        PriceHistoryORM(
            station_id=202,
            fuel_type="diesel_a",
            price=Decimal("1.500"),
            recorded_at=now - timedelta(days=60),  # older than default 30-day window
        )
    )
    await db.commit()

    resp = await api_client.get("/api/v1/stations/202/price-history/diesel_a")
    assert resp.status_code == 200
    assert resp.json() == []  # excluded by 30-day default

    resp2 = await api_client.get("/api/v1/stations/202/price-history/diesel_a?days=90")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
