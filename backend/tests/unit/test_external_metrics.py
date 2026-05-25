"""Unit tests for external-provider and routing-quota metrics."""

import httpx
import pytest

from app.core.metrics import REGISTRY
from app.infrastructure.external.ors.client import ORSClient, ORSClientError
from app.services.routing.quota import DailyQuotaGuard


def _ext(provider: str, outcome: str) -> float:
    return (
        REGISTRY.get_sample_value(
            "datafuel_external_requests_total", {"provider": provider, "outcome": outcome}
        )
        or 0.0
    )


async def test_ors_success_metric() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"distances": [[1.5]], "durations": [[90.0]]})

    client = httpx.AsyncClient(base_url="http://ors.test", transport=httpx.MockTransport(handler))
    before = _ext("ors", "success")
    async with ORSClient(client=client) as ors:
        results = await ors.driving_matrix((39.0, -0.4), [(39.1, -0.5)])
    await client.aclose()

    assert len(results) == 1
    assert _ext("ors", "success") == before + 1.0


async def test_ors_error_metric() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    client = httpx.AsyncClient(base_url="http://ors.test", transport=httpx.MockTransport(handler))
    before = _ext("ors", "error")
    with pytest.raises(ORSClientError):
        async with ORSClient(client=client) as ors:
            await ors.driving_matrix((39.0, -0.4), [(39.1, -0.5)])
    await client.aclose()

    assert _ext("ors", "error") == before + 1.0


def test_quota_guard_updates_gauges_and_fallback_counter() -> None:
    guard = DailyQuotaGuard()
    assert guard.try_acquire(2) is True
    assert REGISTRY.get_sample_value("datafuel_tomtom_quota_used") == 1.0
    assert REGISTRY.get_sample_value("datafuel_tomtom_quota_limit") == 2.0

    guard.try_acquire(2)  # used == 2 (limit reached)
    fb_before = (
        REGISTRY.get_sample_value("datafuel_routing_fallbacks_total", {"provider": "tomtom"})
        or 0.0
    )
    assert guard.try_acquire(2) is False  # breach → fallback
    fb_after = (
        REGISTRY.get_sample_value("datafuel_routing_fallbacks_total", {"provider": "tomtom"})
        or 0.0
    )
    assert fb_after == fb_before + 1.0
