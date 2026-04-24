"""Integration tests for GET /api/v1/recommendations."""

from decimal import Decimal

import pytest

from app.infrastructure.database.models.station import StationORM

USER_LAT = 39.47
USER_LON = -0.376


def _station(station_id: int, lat: float, lon: float, **prices) -> StationORM:
    defaults = {
        "price_gasoline_95_e5": Decimal("1.595"),
        "price_gasoline_95_e10": None,
        "price_gasoline_98_e5": Decimal("1.699"),
        "price_diesel_a": Decimal("1.489"),
        "price_diesel_premium": None,
    }
    defaults.update(prices)
    return StationORM(
        id=station_id,
        brand="TEST",
        address="Calle X",
        locality="Valencia",
        municipality="Valencia",
        province="Valencia",
        postal_code="46001",
        latitude=lat,
        longitude=lon,
        schedule="L-D: 24H",
        **defaults,
    )


@pytest.fixture
async def two_stations(db):
    near = _station(1, 39.471, -0.377)  # ~0.1 km away
    far = _station(2, 39.80, -0.376, price_gasoline_95_e5=Decimal("1.500"))  # ~36 km, cheaper
    db.add_all([near, far])
    await db.commit()


# ── happy path ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recommendations_returns_ranked_list(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "gasoline_95_e5"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Cheapest total cost first.
    assert data[0]["total_cost"] <= data[1]["total_cost"]


@pytest.mark.asyncio
async def test_recommendations_response_fields(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "diesel_a"},
    )
    assert resp.status_code == 200
    item = resp.json()[0]
    for field in (
        "station_id", "brand", "latitude", "longitude",
        "price_per_liter", "fuel_cost", "travel_cost", "total_cost",
        "distance_km", "fuel_type",
    ):
        assert field in item, f"missing field: {field}"


@pytest.mark.asyncio
async def test_recommendations_limit(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "gasoline_95_e5", "limit": 1},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_recommendations_max_distance_filter(api_client, two_stations):
    # max 5 km → only near station (station 1) passes.
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT, "lon": USER_LON,
            "liters": 40, "fuel_type": "gasoline_95_e5",
            "max_distance_km": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["station_id"] == 1


@pytest.mark.asyncio
async def test_recommendations_custom_km_cost(api_client, two_stations):
    # km_cost=0 → travel cost = 0 → cheapest price wins regardless of distance.
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT, "lon": USER_LON,
            "liters": 40, "fuel_type": "gasoline_95_e5",
            "km_cost": 0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # Station 2 has price 1.500, cheaper than station 1 (1.595).
    assert data[0]["station_id"] == 2


@pytest.mark.asyncio
async def test_recommendations_no_matching_fuel(api_client, db, engine):
    # Only diesel_premium station in DB, querying for 95_e10 → empty.
    s = _station(99, 39.47, -0.376, price_gasoline_95_e5=None, price_diesel_a=None)
    db.add(s)
    await db.commit()
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "gasoline_95_e10"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_recommendations_empty_db(api_client, engine):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "diesel_a"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── validation ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recommendations_missing_required_params(api_client, engine):
    resp = await api_client.get("/api/v1/recommendations", params={"lat": 39.47})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recommendations_invalid_fuel_type(api_client, engine):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "jet_fuel"},
    )
    assert resp.status_code == 422
