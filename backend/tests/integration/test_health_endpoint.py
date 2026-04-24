"""Integration tests for the FastAPI app and /api/v1/health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


async def test_health_returns_ok(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "version": "0.1.0", "name": "Data Fuel API"}


async def test_openapi_hidden_when_debug_disabled(api_client: AsyncClient) -> None:
    # Production-safe default: docs/openapi suppressed unless DEBUG=true.
    response = await api_client.get("/openapi.json")
    assert response.status_code == 404


async def test_openapi_exposed_when_debug_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    get_settings.cache_clear()

    app = create_app()
    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]


async def test_cors_allows_configured_origin(api_client: AsyncClient) -> None:
    response = await api_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://example.test"


async def test_cors_blocks_unknown_origin(api_client: AsyncClient) -> None:
    response = await api_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://malicious.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    # FastAPI/Starlette returns 400 when the origin is not in the allow list.
    assert "access-control-allow-origin" not in response.headers
