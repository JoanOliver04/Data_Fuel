"""Integration tests for /api/v1/analytics/* (deterministic, seeded data)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import REGISTRY
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

_NOW = datetime.now(UTC).replace(tzinfo=None)


def _station(sid: int, municipality: str, brand: str, g95: str, lat: float, lon: float) -> StationORM:
    return StationORM(
        id=sid, brand=brand, address="Calle X", locality=municipality,
        municipality=municipality, province="Valencia", postal_code="46000",
        latitude=lat, longitude=lon, schedule="L-D: 24H",
        price_gasoline_95_e5=Decimal(g95), price_gasoline_95_e10=None,
        price_gasoline_98_e5=None, price_diesel_a=Decimal("1.489"), price_diesel_premium=None,
    )


def _history(sid: int, prices: list[str]) -> list[PriceHistoryORM]:
    return [
        PriceHistoryORM(
            station_id=sid, fuel_type="gasolina_95", price=Decimal(p),
            recorded_at=_NOW - timedelta(days=i),
        )
        for i, p in enumerate(prices)
    ]


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    # Two municipalities in the same comarca (La Ribera Alta); CEPSA cheaper.
    db.add_all([
        _station(1, "Alzira", "REPSOL", "1.600", 39.15, -0.43),
        _station(2, "Algemesí", "CEPSA", "1.500", 39.19, -0.44),
    ])
    db.add_all(_history(1, ["1.61", "1.60", "1.60", "1.59", "1.60"]))
    db.add_all(_history(2, ["1.50", "1.50", "1.49", "1.51", "1.50"]))
    await db.commit()


async def test_overview(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_stations"] == 2
    assert body["total_observations"] == 10
    assert "gasolina_95" in body["fuel_averages"]
    assert body["insight"]["text"]
    assert body["insight"]["source"] == "deterministic"


async def test_trends_all_series(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get(
        "/api/v1/analytics/trends", params={"fuel_type": "gasolina_95", "range": "7d"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["group_by"] == "none"
    assert len(body["series"]) == 1
    assert body["series"][0]["label"] == "all"
    assert len(body["series"][0]["points"]) >= 1


async def test_trends_by_brand(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get(
        "/api/v1/analytics/trends",
        params={"fuel_type": "gasolina_95", "range": "7d", "group_by": "brand"},
    )
    assert resp.status_code == 200
    labels = {s["label"] for s in resp.json()["series"]}
    assert labels <= {"REPSOL", "CEPSA"} and labels


async def test_comarcas_sorted_cheapest_first(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get(
        "/api/v1/analytics/comarcas", params={"fuel_type": "gasolina_95", "range": "30d"}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items and items[0]["comarca"] == "La Ribera Alta"
    prices = [i["avg_price"] for i in items]
    assert prices == sorted(prices)


async def test_brands_ranked(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get(
        "/api/v1/analytics/brands", params={"fuel_type": "gasolina_95", "range": "30d"}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["rank"] == 1
    assert items[0]["brand"] == "CEPSA"  # cheaper average


async def test_heatmap(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get(
        "/api/v1/analytics/heatmap", params={"fuel_type": "gasolina_95"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert all("price" in p for p in body["points"])


async def test_insights_bundle(api_client: AsyncClient, seeded: None) -> None:
    resp = await api_client.get(
        "/api/v1/analytics/insights", params={"fuel_type": "gasolina_95", "range": "7d"}
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


async def test_cache_hit_on_repeat(api_client: AsyncClient, seeded: None) -> None:
    before = REGISTRY.get_sample_value(
        "datafuel_analytics_cache_operations_total", {"result": "hit"}
    ) or 0.0
    await api_client.get("/api/v1/analytics/overview")
    await api_client.get("/api/v1/analytics/overview")
    after = REGISTRY.get_sample_value(
        "datafuel_analytics_cache_operations_total", {"result": "hit"}
    ) or 0.0
    assert after >= before + 1.0


async def test_empty_dataset_degrades_gracefully(api_client: AsyncClient, seeded: None) -> None:
    # gasoil_premium has no history → empty series + fallback insight.
    trends = await api_client.get(
        "/api/v1/analytics/trends", params={"fuel_type": "gasoil_premium", "range": "7d"}
    )
    assert trends.status_code == 200
    assert trends.json()["series"][0]["points"] == []
    comarcas = await api_client.get(
        "/api/v1/analytics/comarcas", params={"fuel_type": "gasoil_premium", "range": "30d"}
    )
    assert comarcas.status_code == 200
    assert comarcas.json()["items"] == []
