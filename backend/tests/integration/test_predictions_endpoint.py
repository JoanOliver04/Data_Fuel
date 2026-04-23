"""Integration tests for GET /api/v1/predictions/{station_id}/{fuel_type}."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.services.prediction_service import MIN_SAMPLES
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM


def _station(station_id: int = 1) -> StationORM:
    return StationORM(
        id=station_id,
        brand="REPSOL",
        address="Calle X",
        locality="Valencia",
        municipality="Valencia",
        province="Valencia",
        postal_code="46001",
        latitude=39.47,
        longitude=-0.376,
        schedule="L-D: 24H",
        price_gasoline_95_e5=Decimal("1.595"),
        price_gasoline_95_e10=None,
        price_gasoline_98_e5=None,
        price_diesel_a=Decimal("1.489"),
        price_diesel_premium=None,
    )


def _price_rows(station_id: int, n: int) -> list[PriceHistoryORM]:
    base = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    return [
        PriceHistoryORM(
            station_id=station_id,
            fuel_type="diesel_a",
            price=Decimal(str(round(1.489 + (i % 5) * 0.01, 3))),
            recorded_at=base + timedelta(hours=i * 3),
        )
        for i in range(n)
    ]


@pytest.fixture
async def seeded_station(db):
    station = _station()
    db.add(station)
    await db.flush()
    rows = _price_rows(station.id, MIN_SAMPLES)
    db.add_all(rows)
    await db.commit()


@pytest.fixture
async def station_no_price(db):
    station = StationORM(
        id=2,
        brand="BP",
        address="Av Y",
        locality="Madrid",
        municipality="Madrid",
        province="Madrid",
        postal_code="28001",
        latitude=40.41,
        longitude=-3.7,
        schedule="L-V: 8-20",
        price_gasoline_95_e5=None,
        price_gasoline_95_e10=None,
        price_gasoline_98_e5=None,
        price_diesel_a=None,
        price_diesel_premium=None,
    )
    db.add(station)
    await db.commit()


@pytest.fixture
async def station_insufficient_data(db):
    station = _station(station_id=3)
    db.add(station)
    await db.flush()
    rows = _price_rows(3, MIN_SAMPLES - 1)  # not enough
    db.add_all(rows)
    await db.commit()


# ── happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prediction_returns_200(api_client, seeded_station):
    resp = await api_client.get("/api/v1/predictions/1/diesel_a")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_prediction_response_fields(api_client, seeded_station):
    resp = await api_client.get("/api/v1/predictions/1/diesel_a")
    data = resp.json()
    for field in (
        "station_id", "fuel_type", "current_price",
        "predicted_price", "change_pct", "advice",
        "horizon_hours", "model_r2",
    ):
        assert field in data, f"missing field: {field}"


@pytest.mark.asyncio
async def test_prediction_correct_station_and_fuel(api_client, seeded_station):
    resp = await api_client.get("/api/v1/predictions/1/diesel_a")
    data = resp.json()
    assert data["station_id"] == 1
    assert data["fuel_type"] == "diesel_a"
    assert data["horizon_hours"] == 48


@pytest.mark.asyncio
async def test_prediction_current_price_matches_station(api_client, seeded_station):
    resp = await api_client.get("/api/v1/predictions/1/diesel_a")
    data = resp.json()
    assert abs(data["current_price"] - 1.489) < 0.001


# ── error cases ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prediction_station_not_found(api_client, engine):
    resp = await api_client.get("/api/v1/predictions/999/diesel_a")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_prediction_no_price_for_fuel_type(api_client, station_no_price):
    resp = await api_client.get("/api/v1/predictions/2/diesel_a")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_prediction_insufficient_data(api_client, station_insufficient_data):
    resp = await api_client.get("/api/v1/predictions/3/diesel_a")
    assert resp.status_code == 404
