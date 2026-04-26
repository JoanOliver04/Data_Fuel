"""Integration tests for GET /api/v1/stations/heatmap."""

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
        brand="REPSOL",
        address="Av Test 1",
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
async def three_stations(db):
    cheap = _station(1, 39.471, -0.377, price_diesel_a=Decimal("1.400"))
    mid = _station(2, 39.475, -0.380, price_diesel_a=Decimal("1.550"))
    pricey = _station(3, 39.480, -0.370, price_diesel_a=Decimal("1.700"))
    db.add_all([cheap, mid, pricey])
    await db.commit()


# ── valid GeoJSON envelope ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_heatmap_returns_valid_geojson(api_client, three_stations):
    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 10, "fuel": "gasoil"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    assert len(data["features"]) == 3

    for feature in data["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        # GeoJSON RFC 7946 mandates [lon, lat] order
        coords = feature["geometry"]["coordinates"]
        assert len(coords) == 2
        lon, lat = coords
        assert -180 <= lon <= 180
        assert -90 <= lat <= 90

        props = feature["properties"]
        for field in ("id", "price", "price_normalized", "brand", "name"):
            assert field in props
        assert 0.0 <= props["price_normalized"] <= 1.0


@pytest.mark.asyncio
async def test_heatmap_normalizes_to_endpoints(api_client, three_stations):
    """Cheapest station hits 0.0, most expensive hits 1.0."""
    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 10, "fuel": "gasoil"},
    )
    by_id = {f["properties"]["id"]: f["properties"] for f in resp.json()["features"]}
    assert by_id[1]["price_normalized"] == 0.0
    assert by_id[3]["price_normalized"] == 1.0
    assert 0.0 < by_id[2]["price_normalized"] < 1.0


# ── filtering ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_heatmap_respects_radius(api_client, db):
    near = _station(10, USER_LAT + 0.005, USER_LON, price_diesel_a=Decimal("1.500"))
    far = _station(11, USER_LAT + 1.0, USER_LON, price_diesel_a=Decimal("1.500"))
    db.add_all([near, far])
    await db.commit()

    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 5, "fuel": "gasoil"},
    )
    assert resp.status_code == 200
    ids = [f["properties"]["id"] for f in resp.json()["features"]]
    assert ids == [10]


@pytest.mark.asyncio
async def test_heatmap_skips_stations_without_requested_fuel(api_client, db):
    """A station that doesn't sell the requested fuel must not appear."""
    has_diesel = _station(20, 39.471, -0.377, price_diesel_a=Decimal("1.500"))
    no_diesel = _station(21, 39.472, -0.378, price_diesel_a=None)
    db.add_all([has_diesel, no_diesel])
    await db.commit()

    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 10, "fuel": "gasoil"},
    )
    ids = [f["properties"]["id"] for f in resp.json()["features"]]
    assert ids == [20]


@pytest.mark.asyncio
async def test_heatmap_empty_when_nothing_in_range(api_client, db):
    far = _station(30, USER_LAT + 5.0, USER_LON, price_diesel_a=Decimal("1.500"))
    db.add(far)
    await db.commit()

    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 5, "fuel": "gasoil"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"type": "FeatureCollection", "features": []}


# ── validation ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_heatmap_rejects_invalid_radius(api_client, engine):
    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 0, "fuel": "gasoil"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_heatmap_rejects_unknown_fuel(api_client, engine):
    resp = await api_client.get(
        "/api/v1/stations/heatmap",
        params={"lat": USER_LAT, "lon": USER_LON, "radius_km": 10, "fuel": "kerosene"},
    )
    assert resp.status_code == 422
