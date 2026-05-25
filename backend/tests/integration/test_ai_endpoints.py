"""Integration tests for the /api/v1/ai/* endpoints (deterministic, no LLM)."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.station import StationORM

USER = {"lat": 39.47, "lon": -0.376}


def _station(station_id: int, lat: float, lon: float) -> StationORM:
    return StationORM(
        id=station_id, brand="TEST", address="Calle X", locality="Valencia",
        municipality="Valencia", province="Valencia", postal_code="46001",
        latitude=lat, longitude=lon, schedule="L-D: 24H",
        price_gasoline_95_e5=Decimal("1.595"), price_gasoline_95_e10=None,
        price_gasoline_98_e5=Decimal("1.699"), price_diesel_a=Decimal("1.489"),
        price_diesel_premium=None,
    )


@pytest.fixture
async def one_station(db: AsyncSession) -> None:
    db.add(_station(1, 39.471, -0.377))
    await db.commit()


async def test_explain_recommendation_fallback(api_client: AsyncClient, one_station: None) -> None:
    resp = await api_client.get(
        "/api/v1/ai/explain-recommendation",
        params={**USER, "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"  # no LLM key in tests
    assert body["verdict"] in {"REFUEL_NOW", "WAIT", "NEUTRAL"}
    assert body["summary"]
    assert body["prompt_version"]
    assert isinstance(body["reasoning"], list)


async def test_explain_recommendation_404_when_no_stations(api_client: AsyncClient) -> None:
    resp = await api_client.get(
        "/api/v1/ai/explain-recommendation",
        params={"lat": 10.0, "lon": 10.0, "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 404


async def test_trend_summary_requires_area(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/ai/trend-summary", params={"fuel_type": "gasolina_95"})
    assert resp.status_code == 422


async def test_trend_summary_fallback(api_client: AsyncClient) -> None:
    resp = await api_client.get(
        "/api/v1/ai/trend-summary",
        params={"fuel_type": "gasolina_95", "comarca": "Ribera Alta"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert body["direction"] == "STABLE"  # no price history → stable


async def test_chat_rejects_empty_after_sanitization(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/api/v1/ai/chat",
        json={"question": "\x00\x07", **USER, "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 422


async def test_chat_fallback_with_station(api_client: AsyncClient, one_station: None) -> None:
    resp = await api_client.post(
        "/api/v1/ai/chat",
        json={"question": "¿por qué recomiendas esta estación?", **USER,
              "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "chat"
    assert body["source"] == "fallback"
