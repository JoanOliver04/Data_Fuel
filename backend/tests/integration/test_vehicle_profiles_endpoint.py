"""Integration tests for vehicle-profiles endpoints and recommendations with vehicle_profile_id."""

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


@pytest.fixture
async def profile(db):
    """Vehicle profile: 7 L/100km, reference price 1.50 → km_cost = 0.105."""
    p = VehicleProfileORM(
        name="Mi Coche",
        fuel_consumption_per_100km=7.0,
        tank_capacity_litres=50.0,
        km_cost_per_km=0.105,
        driving_style="mixed",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.fixture
async def two_stations(db):
    near = _station(1, 39.471, -0.377)
    far = _station(2, 39.80, -0.376, price_gasoline_95_e5=Decimal("1.500"))
    db.add_all([near, far])
    await db.commit()


# ── CRUD: vehicle profiles ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_vehicle_profile(api_client, engine):
    resp = await api_client.post(
        "/api/v1/vehicle-profiles",
        json={
            "name": "Mi Coche",
            "fuel_consumption_per_100km": 6.5,
            "tank_capacity_litres": 50,
            "driving_style": "mixed",
            "reference_fuel_price": 1.52,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mi Coche"
    assert data["fuel_consumption_per_100km"] == 6.5
    # K = 6.5/100 * 1.52 = 0.0988
    assert data["km_cost_per_km"] == pytest.approx(0.0988, rel=1e-4)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_electric_profile(api_client, engine):
    resp = await api_client.post(
        "/api/v1/vehicle-profiles",
        json={
            "name": "Tesla",
            "fuel_consumption_per_100km": 0,
            "tank_capacity_litres": 0.1,
            "driving_style": "urban",
            "reference_fuel_price": 1.50,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["km_cost_per_km"] == 0.0


@pytest.mark.asyncio
async def test_list_vehicle_profiles(api_client, profile):
    resp = await api_client.get("/api/v1/vehicle-profiles")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Mi Coche"


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
async def test_update_vehicle_profile(api_client, profile):
    resp = await api_client.put(
        f"/api/v1/vehicle-profiles/{profile.id}",
        json={"name": "Coche Nuevo", "fuel_consumption_per_100km": 8.0, "reference_fuel_price": 1.60},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Coche Nuevo"
    # K = 8.0/100 * 1.60 = 0.128
    assert data["km_cost_per_km"] == pytest.approx(0.128, rel=1e-4)


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
    assert data["consumption_l_per_100km"] == 6.5
    assert data["fuel_price_eur_per_l"] == 1.52


@pytest.mark.asyncio
async def test_estimate_km_cost_electric(api_client, engine):
    resp = await api_client.get(
        "/api/v1/vehicle-profiles/estimate-km-cost",
        params={"consumption": 0, "fuel_price": 1.80},
    )
    assert resp.status_code == 200
    assert resp.json()["km_cost_eur_per_km"] == 0.0


@pytest.mark.asyncio
async def test_estimate_km_cost_high_consumption(api_client, engine):
    resp = await api_client.get(
        "/api/v1/vehicle-profiles/estimate-km-cost",
        params={"consumption": 15, "fuel_price": 2.0},
    )
    assert resp.status_code == 200
    assert resp.json()["km_cost_eur_per_km"] == pytest.approx(0.30, rel=1e-4)


# ── recommendations with vehicle_profile_id ────────────────────────────────


@pytest.mark.asyncio
async def test_recommendations_with_profile_uses_dynamic_k(api_client, profile, two_stations):
    """With a 7 L/100km profile and avg price ~1.548, K ≈ 0.1083 — different from default 0.13."""
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT,
            "lon": USER_LON,
            "liters": 40,
            "fuel_type": "gasolina_95",
            "vehicle_profile_id": profile.id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    # km_cost in the response should NOT be the default 0.13.
    km_cost_used = data[0]["km_cost"]
    assert km_cost_used != pytest.approx(0.13, abs=0.005)


@pytest.mark.asyncio
async def test_recommendations_profile_not_found_returns_404(api_client, two_stations):
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
async def test_recommendations_electric_profile_zero_travel_cost(api_client, db, engine):
    """Electric profile → K=0 → travel_cost=0 for all results."""
    electric = VehicleProfileORM(
        name="Tesla",
        fuel_consumption_per_100km=0.0,
        tank_capacity_litres=0.1,
        km_cost_per_km=0.0,
        driving_style="urban",
    )
    db.add(electric)
    station = _station(10, 39.80, -0.376)
    db.add(station)
    await db.commit()
    await db.refresh(electric)

    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT,
            "lon": USER_LON,
            "liters": 40,
            "fuel_type": "gasolina_95",
            "vehicle_profile_id": electric.id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert float(data[0]["travel_cost"]) == pytest.approx(0.0, abs=0.001)
    assert float(data[0]["km_cost"]) == 0.0


# ── validation ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_profile_invalid_consumption(api_client, engine):
    resp = await api_client.post(
        "/api/v1/vehicle-profiles",
        json={
            "name": "Bad",
            "fuel_consumption_per_100km": -1,
            "tank_capacity_litres": 50,
            "driving_style": "mixed",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_missing_name(api_client, engine):
    resp = await api_client.post(
        "/api/v1/vehicle-profiles",
        json={"fuel_consumption_per_100km": 7, "tank_capacity_litres": 50, "driving_style": "mixed"},
    )
    assert resp.status_code == 422
