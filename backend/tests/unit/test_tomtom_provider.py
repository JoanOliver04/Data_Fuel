"""Tests for TomTomMatrixProvider: mapping, graceful fallback, retries, quota.

TomTom is stubbed at httpx.MockTransport level via the real TomTomClient. Each
test uses a fresh DailyQuotaGuard so the process-wide default counter never
leaks between tests. ``backoff_base=0.0`` keeps retry tests instant.
"""

import json

import httpx
import pytest

from app.infrastructure.external.tomtom import TomTomClient
from app.services.routing import RouteLeg, TomTomMatrixProvider
from app.services.routing.quota import DailyQuotaGuard

USER = (39.47, -0.376)
DESTINATIONS = [(39.48, -0.37), (39.49, -0.36)]
_HIGH_LIMIT = 2400


def _build_mock_client(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url="https://tomtom.test")


def _cell(dest_index: int, length_m: int, time_s: int, traffic_s: int = 0) -> dict[str, object]:
    return {
        "originIndex": 0,
        "destinationIndex": dest_index,
        "routeSummary": {
            "lengthInMeters": length_m,
            "travelTimeInSeconds": time_s,
            "trafficDelayInSeconds": traffic_s,
        },
    }


def _matrix_body(cells: list[dict[str, object]]) -> bytes:
    return json.dumps({"data": cells}).encode()


def _provider(mock_client: httpx.AsyncClient, *, limit: int = _HIGH_LIMIT,
              max_retries: int = 3) -> TomTomMatrixProvider:
    client = TomTomClient(
        api_key="fake", client=mock_client, max_retries=max_retries, backoff_base=0.0
    )
    return TomTomMatrixProvider(client, daily_quota_limit=limit, quota_guard=DailyQuotaGuard())


# ── happy path / mapping ───────────────────────────────────────────────────────


async def test_maps_meters_seconds_and_traffic() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_matrix_body([
            _cell(0, 4200, 480, 60),
            _cell(1, 7500, 900, 0),
        ]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        legs = await _provider(mock_client).matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(legs) == 2
    assert all(isinstance(leg, RouteLeg) for leg in legs)
    assert legs[0].provider == "tomtom" and legs[0].failed is False
    assert legs[0].distance_km == pytest.approx(4.2)  # 4200 m → km
    assert legs[0].duration_seconds == 480
    assert legs[0].traffic_delay_seconds == 60
    assert legs[1].distance_km == pytest.approx(7.5)
    assert legs[1].traffic_delay_seconds == 0


async def test_empty_destinations_returns_empty() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("must not call TomTom for empty destinations")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        assert await _provider(mock_client).matrix(USER, []) == []
    finally:
        await mock_client.aclose()


# ── graceful fallback ──────────────────────────────────────────────────────────


async def test_missing_cell_degrades_only_that_leg() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        # Destination 1 not routed → no cell → that leg falls back.
        return httpx.Response(200, content=_matrix_body([_cell(0, 4200, 480)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        legs = await _provider(mock_client).matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert legs[0].failed is False and legs[0].provider == "tomtom"
    assert legs[1].failed is True and legs[1].provider == "tomtom"
    assert legs[1].duration_seconds is None
    assert legs[1].distance_km > 0  # haversine fallback


async def test_total_failure_degrades_all_legs() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request")  # non-retryable → TomTomError

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        legs = await _provider(mock_client).matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(legs) == 2
    assert all(leg.provider == "tomtom" and leg.failed is True for leg in legs)
    assert all(leg.duration_seconds is None for leg in legs)
    assert all(leg.distance_km > 0 for leg in legs)


async def test_rate_limit_after_retries_degrades_to_haversine() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        # max_retries=1 → client raises TomTomRateLimitError → provider must not raise.
        legs = await _provider(mock_client, max_retries=1).matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert all(leg.failed is True and leg.provider == "tomtom" for leg in legs)


# ── retries ────────────────────────────────────────────────────────────────────


async def test_retries_on_503_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, content=_matrix_body([_cell(0, 4200, 480), _cell(1, 7500, 900)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        legs = await _provider(mock_client).matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert calls["n"] == 3  # 2 failures + 1 success
    assert all(leg.failed is False and leg.provider == "tomtom" for leg in legs)


# ── quota handling ─────────────────────────────────────────────────────────────


async def test_quota_exhausted_short_circuits_without_calling_tomtom() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("TomTom must not be called when quota is exhausted")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        # limit=0 → guard refuses immediately, every leg falls back to haversine.
        legs = await _provider(mock_client, limit=0).matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(legs) == 2
    assert all(leg.failed is True and leg.provider == "tomtom" for leg in legs)
    assert all(leg.distance_km > 0 for leg in legs)


async def test_quota_consumed_one_per_call() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_matrix_body([_cell(0, 4200, 480)]))

    guard = DailyQuotaGuard()
    mock_client = _build_mock_client(httpx.MockTransport(handler))
    client = TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0)
    provider = TomTomMatrixProvider(client, daily_quota_limit=1, quota_guard=guard)
    try:
        first = await provider.matrix(USER, [(39.48, -0.37)])
        second = await provider.matrix(USER, [(39.48, -0.37)])  # quota now spent
    finally:
        await mock_client.aclose()

    assert first[0].failed is False  # used the single allowed request
    assert second[0].failed is True  # short-circuited to haversine
    assert guard.snapshot(1).exhausted is True
