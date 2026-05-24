"""Tests for the Prometheus /metrics endpoint."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


async def test_metrics_endpoint_exposes_prometheus_text(api_client: AsyncClient) -> None:
    resp = await api_client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    # Build info is published for every app instance.
    assert "datafuel_build_info" in resp.text


async def test_metrics_endpoint_is_not_in_openapi_schema(api_client: AsyncClient) -> None:
    # Docs are only served in DEBUG; build a debug app to inspect the schema.
    schema = create_app().openapi()
    assert "/metrics" not in schema["paths"]


@pytest.fixture
async def disabled_metrics_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("METRICS_ENABLED", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("SYNC_ON_STARTUP", "false")
    get_settings.cache_clear()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_metrics_endpoint_404_when_disabled(
    disabled_metrics_client: AsyncClient,
) -> None:
    resp = await disabled_metrics_client.get("/metrics")
    assert resp.status_code == 404
