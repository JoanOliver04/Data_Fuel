"""Tests for ORSClient using httpx.MockTransport (no real network)."""

import json

import httpx
import pytest

from app.infrastructure.external.ors import ORSClient, ORSClientError


def _build_mock_client(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url="https://ors.test")


async def test_driving_matrix_parses_distance_and_duration() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        body = {
            "distances": [[4.2, 7.5]],
            "durations": [[480.0, 900.0]],
        }
        return httpx.Response(200, content=json.dumps(body).encode())

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with ORSClient(api_key="fake", client=mock_client) as ors:
            results = await ors.driving_matrix(
                origin=(39.47, -0.376),
                destinations=[(39.48, -0.37), (39.49, -0.36)],
            )
    finally:
        await mock_client.aclose()

    assert captured["path"] == "/v2/matrix/driving-car"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["locations"][0] == [-0.376, 39.47]
    assert body["sources"] == [0]
    assert body["destinations"] == [1, 2]

    assert len(results) == 2
    assert results[0].distance_km == pytest.approx(4.2)
    assert results[0].duration_min == pytest.approx(8.0)
    assert results[1].distance_km == pytest.approx(7.5)
    assert results[1].duration_min == pytest.approx(15.0)


async def test_driving_matrix_chunks_large_input() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        n = len(body["destinations"])
        calls.append(n)
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "distances": [[1.0] * n],
                    "durations": [[60.0] * n],
                }
            ).encode(),
        )

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with ORSClient(api_key="fake", chunk_size=3, client=mock_client) as ors:
            results = await ors.driving_matrix(
                origin=(0.0, 0.0),
                destinations=[(float(i), float(i)) for i in range(7)],
            )
    finally:
        await mock_client.aclose()

    assert calls == [3, 3, 1]
    assert len(results) == 7
    assert all(r.distance_km == 1.0 and r.duration_min == 1.0 for r in results)


async def test_http_error_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with ORSClient(api_key="fake", client=mock_client) as ors:
            with pytest.raises(ORSClientError, match="ORS request failed"):
                await ors.driving_matrix((0.0, 0.0), [(1.0, 1.0)])
    finally:
        await mock_client.aclose()


async def test_missing_fields_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{}")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with ORSClient(api_key="fake", client=mock_client) as ors:
            with pytest.raises(ORSClientError, match="Could not parse"):
                await ors.driving_matrix((0.0, 0.0), [(1.0, 1.0)])
    finally:
        await mock_client.aclose()


async def test_empty_destinations_returns_empty() -> None:
    mock_client = _build_mock_client(
        httpx.MockTransport(lambda _: httpx.Response(500))
    )
    try:
        async with ORSClient(api_key="fake", client=mock_client) as ors:
            assert await ors.driving_matrix((0.0, 0.0), []) == []
    finally:
        await mock_client.aclose()


async def test_missing_api_key_raises() -> None:
    client = ORSClient(api_key=None)
    with pytest.raises(ORSClientError, match="ORS_API_KEY"):
        async with client:
            pass
