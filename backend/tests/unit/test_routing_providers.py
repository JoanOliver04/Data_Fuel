"""Tests for the RoutingProvider implementations (HaversineProvider, OrsMatrixProvider).

ORS is stubbed at httpx.MockTransport level via the existing ORSClient — no
patching of internals, no real network.
"""

import json

import httpx
import pytest

from app.infrastructure.external.ors import ORSClient
from app.services.routing import HaversineProvider, OrsMatrixProvider, RouteLeg

USER = (39.47, -0.376)  # Valencia
DESTINATIONS = [(39.48, -0.37), (39.49, -0.36)]


def _build_mock_client(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url="https://ors.test")


# ── HaversineProvider ──────────────────────────────────────────────────────────


async def test_haversine_provider_returns_leg_per_destination() -> None:
    legs = await HaversineProvider().matrix(USER, DESTINATIONS)

    assert len(legs) == 2
    assert all(isinstance(leg, RouteLeg) for leg in legs)
    assert all(leg.provider == "haversine" for leg in legs)
    assert all(leg.failed is False for leg in legs)
    assert all(leg.duration_seconds is None for leg in legs)
    assert all(leg.traffic_delay_seconds is None for leg in legs)
    assert all(leg.distance_km > 0 for leg in legs)


async def test_haversine_provider_empty_destinations() -> None:
    assert await HaversineProvider().matrix(USER, []) == []


# ── OrsMatrixProvider ──────────────────────────────────────────────────────────


async def test_ors_provider_maps_distance_and_duration_seconds() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps(
                {"distances": [[4.2, 7.5]], "durations": [[480.0, 900.0]]}
            ).encode(),
        )

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        provider = OrsMatrixProvider(ORSClient(api_key="fake", client=mock_client))
        legs = await provider.matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(legs) == 2
    assert legs[0].provider == "ors" and legs[0].failed is False
    assert legs[0].distance_km == pytest.approx(4.2)
    assert legs[0].duration_seconds == 480  # 8 min → 480 s
    assert legs[0].traffic_delay_seconds is None
    assert legs[1].distance_km == pytest.approx(7.5)
    assert legs[1].duration_seconds == 900


async def test_ors_provider_total_failure_degrades_all_legs_to_haversine() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        provider = OrsMatrixProvider(ORSClient(api_key="fake", client=mock_client))
        legs = await provider.matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(legs) == 2
    # provider stays "ors" so the caller knows what degraded.
    assert all(leg.provider == "ors" for leg in legs)
    assert all(leg.failed is True for leg in legs)
    assert all(leg.duration_seconds is None for leg in legs)
    assert all(leg.distance_km > 0 for leg in legs)


async def test_ors_provider_unreachable_leg_degrades_only_that_leg() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        # Destination 1 is unreachable → ORS returns null for both metrics.
        return httpx.Response(
            200,
            content=json.dumps(
                {"distances": [[4.2, None]], "durations": [[480.0, None]]}
            ).encode(),
        )

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        provider = OrsMatrixProvider(ORSClient(api_key="fake", client=mock_client))
        legs = await provider.matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert legs[0].failed is False
    assert legs[0].duration_seconds == 480
    assert legs[1].failed is True
    assert legs[1].provider == "ors"
    assert legs[1].duration_seconds is None
    assert legs[1].distance_km > 0  # haversine fallback


async def test_ors_provider_empty_destinations_skips_call() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("ORS must not be called for empty destinations")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        provider = OrsMatrixProvider(ORSClient(api_key="fake", client=mock_client))
        assert await provider.matrix(USER, []) == []
    finally:
        await mock_client.aclose()
