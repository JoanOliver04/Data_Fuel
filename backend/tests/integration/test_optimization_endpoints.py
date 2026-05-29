"""Integration tests for the traffic-aware optimization endpoints."""

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
    near = _station(1, 39.471, -0.377)
    far = _station(2, 39.80, -0.376, price_gasoline_95_e5=Decimal("1.500"))
    db.add_all([near, far])
    await db.commit()


# ── /recommendations?optimization_profile ──────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_call_has_null_optimization_fields(api_client, two_stations):
    """Backwards compatible: no profile → optimization_* fields are null."""
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["optimization_profile"] is None
    assert item["optimization_score"] is None
    assert item["time_cost"] is None


@pytest.mark.asyncio
async def test_profile_populates_optimization_fields(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT, "lon": USER_LON, "liters": 40,
            "fuel_type": "gasolina_95", "optimization_profile": "BALANCED",
        },
    )
    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["optimization_profile"] == "BALANCED"
    assert item["optimization_score"] is not None
    # EUCLIDEAN mode → no driving ETA → time cost and traffic penalty are 0.
    assert item["time_cost"] == 0.0
    assert item["traffic_penalty"] == 0.0
    assert item["eta_minutes"] is None


@pytest.mark.asyncio
async def test_profile_results_sorted_by_score(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT, "lon": USER_LON, "liters": 40,
            "fuel_type": "gasolina_95", "optimization_profile": "CHEAPEST",
        },
    )
    assert resp.status_code == 200
    scores = [item["optimization_score"] for item in resp.json()]
    assert scores == sorted(scores)


@pytest.mark.asyncio
async def test_invalid_profile_is_422(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/recommendations",
        params={
            "lat": USER_LAT, "lon": USER_LON, "liters": 40,
            "fuel_type": "gasolina_95", "optimization_profile": "TURBO",
        },
    )
    assert resp.status_code == 422


# ── /analytics/optimization-summary ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_optimization_summary_shape(api_client, two_stations):
    resp = await api_client.get(
        "/api/v1/analytics/optimization-summary",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"] == "BALANCED"  # default
    assert body["station_count"] == 2
    assert body["average_traffic_delay_minutes"] == 0.0  # EUCLIDEAN
    assert body["average_eta_minutes"] is None
    assert len(body["profile_winners"]) == 4
    assert sum(body["best_profile_distribution"].values()) == 4


@pytest.mark.asyncio
async def test_optimization_summary_empty_db(api_client, engine):
    resp = await api_client.get(
        "/api/v1/analytics/optimization-summary",
        params={"lat": USER_LAT, "lon": USER_LON, "liters": 40, "fuel_type": "gasoil"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["station_count"] == 0
    assert body["profile_winners"] == []
