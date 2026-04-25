"""Tests for the DistanceService: Euclidean, Driving, and silent fallback."""

import json

import httpx
import pytest

from app.domain.services.distance_service import (
    DistanceMode,
    DistanceService,
)
from app.infrastructure.external.ors import ORSClient


def _build_mock_client(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url="https://ors.test")


USER = (39.47, -0.376)  # Valencia
DESTINATIONS = [(39.48, -0.37), (39.49, -0.36)]


async def test_euclidean_mode_uses_haversine() -> None:
    svc = DistanceService(mode=DistanceMode.EUCLIDEAN)

    results = await svc.compute(USER, DESTINATIONS)

    assert len(results) == 2
    assert all(r.driving_distance_km is None for r in results)
    assert all(r.driving_duration_min is None for r in results)
    assert all(r.distance_km > 0 for r in results)


async def test_driving_mode_uses_ors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "distances": [[4.2, 7.5]],
                    "durations": [[480.0, 900.0]],
                }
            ).encode(),
        )

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        ors = ORSClient(api_key="fake", client=mock_client)
        svc = DistanceService(mode=DistanceMode.DRIVING, ors_client=ors)
        results = await svc.compute(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(results) == 2
    assert results[0].distance_km == pytest.approx(4.2)
    assert results[0].driving_distance_km == pytest.approx(4.2)
    assert results[0].driving_duration_min == pytest.approx(8.0)
    assert results[1].driving_duration_min == pytest.approx(15.0)


async def test_driving_mode_falls_back_on_ors_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        ors = ORSClient(api_key="fake", client=mock_client)
        svc = DistanceService(mode=DistanceMode.DRIVING, ors_client=ors)
        results = await svc.compute(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert len(results) == 2
    # Fallback: no driving data, only haversine populated
    assert all(r.driving_distance_km is None for r in results)
    assert all(r.driving_duration_min is None for r in results)
    assert all(r.distance_km > 0 for r in results)


async def test_driving_mode_without_client_falls_back() -> None:
    svc = DistanceService(mode=DistanceMode.DRIVING, ors_client=None)

    results = await svc.compute(USER, DESTINATIONS)

    assert len(results) == 2
    assert all(r.driving_distance_km is None for r in results)
