"""Integration tests for vehicle-profiles endpoints + dynamic K in recommendations."""

from decimal import Decimal

import pytest

from app.infrastructure.database.models.station import StationORM
from app.infrastructure.database.models.vehicle_profile import VehicleProfileORM

USER_LAT = 39.47
USER_LON = -0.376


# ── Fixtures ───────────────────────────────────────────────────────────────


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


VALID_BODY = {
    "name": "Mi Coche",
    "fuel_consumption_urban": 8.0,
    "fuel_consumption_mixed": 6.5,
    "fuel_consumption_highway": 5.5,
    "tank_capacity_litres": 50.0,
    "driving_style": "mixed",
    "reference_fuel_price": 1.52,
}


@pytest.fixture
async def profile(db) -> VehicleProfileORM:
    """Vehicle profile with distinct consumption values per band."""
    p = VehicleProfileORM(
        name="Mi Coche",
        fuel_consumption_urban=8.0,
        fuel_consumption_mixed=6.5,
        fuel_consumption_highway=5.5,
        tank_capacity_litres=50.0,
        km_cost_per_km=0.0988,
        driving_style="mixed",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ── POST: valid data ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_vehicle_profile_valid(api_client, engine):
    resp = await api_client.post("/api/v1/vehicle-profiles", json=VALID_BODY)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Mi Coche"
    assert data["fuel_consumption_urban"] == 8.0
    assert data["fuel_consumption_mixed"] == 6.5
    assert data["fuel_consumption_highway"] == 5.5
    # K stored as reference uses the mixed consumption: 6.5/100 * 1.52 = 0.0988
    assert data["km_cost_per_km"] == pytest.approx(0.0988, rel=1e-4)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_then_list(api_client, engine):
    create = await api_client.post("/api/v1/vehicle-profiles", json=VALID_BODY)
    assert create.status_code == 201
    listing = await api_client.get("/api/v1/vehicle-profiles")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


# ── POST: invalid data ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["fuel_consumption_urban", "fuel_consumption_mixed", "fuel_consumption_highway"])
@pytest.mark.parametrize("bad_value", [0.5, 0.0, 25.5, -1.0, 100.0])
async def test_create_profile_invalid_consumption_out_of_range(api_client, engine, field, bad_value):
    body = {**VALID_BODY, field: bad_value}
    resp = await api_client.post("/api/v1/vehicle-profiles", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_tank", [9.9, 0.0, -1.0, 200.1, 500.0])
async def test_create_profile_invalid_tank(api_client, engine, bad_tank):
    body = {**VALID_BODY, "tank_capacity_litres": bad_tank}
    resp = await api_client.post("/api/v1/vehicle-profiles", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_missing_name(api_client, engine):
    body = {k: v for k, v in VALID_BODY.items() if k != "name"}
    resp = await api_client.post("/api/v1/vehicle-profiles", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_missing_consumption_field(api_client, engine):
    body = {k: v for k, v in VALID_BODY.items() if k != "fuel_consumption_mixed"}
    resp = await api_client.post("/api/v1/vehicle-profiles", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_consumption_at_bounds_is_valid(api_client, engine):
    body = {**VALID_BODY, "fuel_consumption_urban": 1.0, "fuel_consumption_highway": 25.0}
    resp = await api_client.post("/api/v1/vehicle-profiles", json=body)
    assert resp.status_code == 201, resp.text


# ── GET / PUT / DELETE ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_vehicle_profile(api_client, profile):
    resp = await api_client.get(f"/api/v1/vehicle-profiles/{profile.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == profile.id


@pytest.mark.asyncio
async def test_get_vehicle_profile_not_found(api_client, engine):
    resp = await api_client.get("/api/v1/vehicle-profiles/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_vehicle_profile_recomputes_reference_k(api_client, profile):
    resp = await api_client.put(
        f"/api/v1/vehicle-profiles/{profile.id}",
        json={"fuel_consumption_mixed": 8.0, "reference_fuel_price": 1.60},
    )
    assert resp.status_code == 200
    data = resp.json()
    # K = 8.0/100 * 1.60 = 0.128
    assert data["km_cost_per_km"] == pytest.approx(0.128, rel=1e-4)
    assert data["fuel_consumption_mixed"] == 8.0


@pytest.mark.asyncio
async def test_delete_vehicle_profile(api_client, profile):
    resp = await api_client.delete(f"/api/v1/vehicle-profiles/{profile.id}")
    assert resp.status_code == 204
    resp2 = await api_client.get(f"/api/v1/vehicle-profiles/{profile.id}")
    assert resp2.status_code == 404


# ── estimate-km-cost ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_estimate_km_cost_typical(api_client, engine):
    resp = await api_client.get(
        "/api/v1/vehicle-profiles/estimate-km-cost",
        params={"consumption": 6.5, "fuel_price": 1.52},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["km_cost_eur_per_km"] == pytest.approx(0.0988, rel=1e-4)


@pytest.mark.asyncio
async def test_estimate_km_cost_electric(api_client, engine):
    resp = await api_client.get(
        "/api/v1/vehicle-profiles/estimate-km-cost",
        params={"consumption": 0, "fuel_price": 1.80},
    )
    assert resp.status_code == 200
    assert resp.json()["km_cost_eur_per_km"] == 0.0


# ── Recommendations: dynamic consumption per distance ──────────────────────


@pytest.fixture
async def stations_at_distances(db):
    """Three stations at distances ≈3, ≈10, ≈30 km from (39.47, -0.376).

    With our haversine implementation:
      ~3 km  → urban band   (Δlat 0.027 ≈ 3.0 km)
      ~10 km → mixed band   (Δlat 0.090 ≈ 10.0 km)
      ~30 km → highway band (Δlat 0.270 ≈ 30.0 km)
    """
    near = _station(1, USER_LAT + 0.027, USER_LON, price_gasoline_95_e5=Decimal("1.500"))
    mid = _station(2, USER_LAT + 0.090, USER_LON, price_gasoline_95_e5=Decimal("1.500"))
    far = _station(3, USER_LAT + 0.270, USER_LON, price_gasoline_95_e5=Decimal("1.500"))
    db.add_all([near, mid, far])
    await db.commit()


@pytest.mark.asyncio
async def test_recommendations_apply_correct_consumption_per_distance(
    api_client, profile, stations_at_distances
):
    """Each station gets a K computed from the distance band's consumption * that station's price.

    profile: urban=8, mixed=6.5, highway=5.5; all stations have price 1.500 €/L.
      K_urban   = 8.0/100   * 1.5 = 0.120
      K_mixed   = 6.5/100   * 1.5 = 0.0975
      K_highway = 5.5/100   * 1.5 = 0.0825
    """
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT,
            "lon": USER_LON,
            "liters": 40,
            "fuel_type": "gasolina_95",
            "vehicle_profile_id": profile.id,
            "limit": 50,
        },
    )
    assert resp.status_code == 200
    items = {item["station_id"]: item for item in resp.json()}
    assert set(items) == {1, 2, 3}

    near, mid, far = items[1], items[2], items[3]

    assert near["consumption_mode"] == "urban"
    assert near["consumption_l_per_100km"] == pytest.approx(8.0)
    assert near["km_cost"] == pytest.approx(0.120, rel=1e-3)

    assert mid["consumption_mode"] == "mixed"
    assert mid["consumption_l_per_100km"] == pytest.approx(6.5)
    assert mid["km_cost"] == pytest.approx(0.0975, rel=1e-3)

    assert far["consumption_mode"] == "highway"
    assert far["consumption_l_per_100km"] == pytest.approx(5.5)
    assert far["km_cost"] == pytest.approx(0.0825, rel=1e-3)


@pytest.mark.asyncio
async def test_recommendations_use_per_station_price_for_k(api_client, profile, db):
    """Two highway-band stations with different prices → different K values."""
    cheap = _station(10, USER_LAT + 0.270, USER_LON, price_gasoline_95_e5=Decimal("1.400"))
    pricey = _station(11, USER_LAT + 0.270, USER_LON + 0.001, price_gasoline_95_e5=Decimal("1.700"))
    db.add_all([cheap, pricey])
    await db.commit()

    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT,
            "lon": USER_LON,
            "liters": 40,
            "fuel_type": "gasolina_95",
            "vehicle_profile_id": profile.id,
            "limit": 50,
        },
    )
    assert resp.status_code == 200
    items = {item["station_id"]: item for item in resp.json()}
    # Both highway band; K = 5.5/100 * price
    assert items[10]["km_cost"] == pytest.approx(0.077, rel=1e-3)
    assert items[11]["km_cost"] == pytest.approx(0.0935, rel=1e-3)


@pytest.mark.asyncio
async def test_recommendations_profile_not_found_returns_404(api_client, stations_at_distances):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT,
            "lon": USER_LON,
            "liters": 40,
            "fuel_type": "gasolina_95",
            "vehicle_profile_id": 9999,
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_recommendations_without_profile_uses_static_km_cost(
    api_client, stations_at_distances
):
    """No vehicle_profile_id → consumption_mode is null; static km_cost is applied."""
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT,
            "lon": USER_LON,
            "liters": 40,
            "fuel_type": "gasolina_95",
            "km_cost": 0.13,
            "limit": 50,
        },
    )
    assert resp.status_code == 200
    for item in resp.json():
        assert item["consumption_mode"] is None
        assert item["consumption_l_per_100km"] is None
        assert item["km_cost"] == pytest.approx(0.13)
