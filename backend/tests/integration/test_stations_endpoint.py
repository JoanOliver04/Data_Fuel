"""Integration tests for the /api/v1/stations endpoints."""

from decimal import Decimal

import pytest

from app.infrastructure.database.models.station import StationORM

# ── fixtures ───────────────────────────────────────────────────────────────


def _station_orm(
    station_id: int,
    province: str = "Valencia",
    municipality: str = "Valencia",
    brand: str = "REPSOL",
) -> StationORM:
    return StationORM(
        id=station_id,
        brand=brand,
        address=f"Calle Test {station_id}",
        locality=municipality,
        municipality=municipality,
        province=province,
        postal_code="46001",
        latitude=39.47,
        longitude=-0.376,
        schedule="L-D: 24H",
        price_gasoline_95_e5=Decimal("1.595"),
        price_diesel_a=Decimal("1.489"),
        price_gasoline_95_e10=None,
        price_gasoline_98_e5=Decimal("1.699"),
        price_diesel_premium=None,
    )


@pytest.fixture
async def stations_in_db(db):
    """Insert two stations from different provinces."""
    s1 = _station_orm(1001, province="Valencia", municipality="Valencia")
    s2 = _station_orm(1002, province="Madrid", municipality="Madrid", brand="CEPSA")
    db.add_all([s1, s2])
    await db.commit()
    return [s1, s2]


# ── GET /stations ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_stations_returns_all(api_client, stations_in_db):
    resp = await api_client.get("/api/v1/stations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_stations_filter_province(api_client, stations_in_db):
    resp = await api_client.get("/api/v1/stations", params={"province": "Madrid"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["province"] == "Madrid"


@pytest.mark.asyncio
async def test_list_stations_filter_municipality(api_client, stations_in_db):
    resp = await api_client.get("/api/v1/stations", params={"municipality": "Valencia"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["municipality"] == "Valencia"


@pytest.mark.asyncio
async def test_list_stations_empty(api_client, engine):
    """No stations in DB returns an empty list, not an error."""
    resp = await api_client.get("/api/v1/stations")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_station_prices_shape(api_client, stations_in_db):
    resp = await api_client.get("/api/v1/stations")
    assert resp.status_code == 200
    station = resp.json()[0]
    prices = station["prices"]
    assert "gasoline_95_e5" in prices
    assert "diesel_a" in prices
    assert "diesel_premium" in prices


# ── GET /stations/{id} ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_station_by_id(api_client, stations_in_db):
    resp = await api_client.get("/api/v1/stations/1001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1001
    assert data["brand"] == "REPSOL"


@pytest.mark.asyncio
async def test_get_station_not_found(api_client, engine):
    resp = await api_client.get("/api/v1/stations/9999")
    assert resp.status_code == 404
