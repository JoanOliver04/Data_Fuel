"""Tests for liveness / readiness / detailed health endpoints."""

import pytest
from httpx import AsyncClient


async def test_liveness_always_alive(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"
    assert body["uptime_seconds"] >= 0.0


async def test_readiness_degraded_when_model_absent_but_db_ok(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/health/ready")
    assert resp.status_code == 200  # DB is the only hard gate
    body = resp.json()
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["model"]["ok"] is False  # not loaded under ASGITransport
    assert body["status"] in {"ready", "degraded"}


async def test_readiness_503_when_db_unreachable(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom() -> None:
        raise RuntimeError("db gone")

    monkeypatch.setattr("app.api.v1.endpoints.health.get_session_factory", _boom)
    resp = await api_client.get("/api/v1/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["ok"] is False
    assert body["checks"]["database"]["detail"] == "RuntimeError"


async def test_details_reports_subsystems(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/health/details")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"]["ok"] is True
    assert body["providers"]["distance_mode"] == "EUCLIDEAN"
    assert body["providers"]["routing_provider"] == "HaversineProvider"
    assert body["scheduler"]["enabled"] is False  # disabled in test settings
    assert body["model"]["loaded"] is False
    assert "recommendations_size" in body["cache"]


async def test_legacy_health_contract_unchanged(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "name" in body
