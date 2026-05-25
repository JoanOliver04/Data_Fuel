"""Tests for sanitised, request-correlated error handling."""

import json

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.config import get_settings
from app.core.errors import unhandled_exception_handler
from app.core.metrics import REGISTRY
from app.main import create_app


def _request_with_ids() -> Request:
    req = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    req.state.request_id = "rid1"
    req.state.correlation_id = "cid1"
    return req


async def test_sanitized_500_hides_internal_details(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()
    resp = await unhandled_exception_handler(_request_with_ids(), ValueError("super secret"))
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body["detail"] == "Internal Server Error"
    assert body["request_id"] == "rid1"
    assert body["correlation_id"] == "cid1"
    assert "super secret" not in resp.body.decode()


async def test_debug_mode_includes_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()
    resp = await unhandled_exception_handler(_request_with_ids(), ValueError("boom"))
    body = json.loads(resp.body)
    assert body["exception"] == "ValueError: boom"


async def test_unhandled_exception_returns_correlated_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("SYNC_ON_STARTUP", "false")
    get_settings.cache_clear()

    app = create_app()
    app.state.limiter.enabled = False

    @app.get("/api/v1/_boom")
    async def _boom() -> None:
        raise RuntimeError("kaboom")

    labels = {"method": "GET", "route": "/api/v1/_boom"}
    before = REGISTRY.get_sample_value("datafuel_http_exceptions_total", labels) or 0.0

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/_boom")

    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal Server Error"
    assert "kaboom" not in resp.text  # internal message never leaks
    assert len(body["request_id"]) > 0  # correlated to the request

    after = REGISTRY.get_sample_value("datafuel_http_exceptions_total", labels) or 0.0
    assert after == before + 1.0
