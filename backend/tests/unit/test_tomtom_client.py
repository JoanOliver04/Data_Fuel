"""Tests for TomTomClient using httpx.MockTransport (no real network).

Retry tests pass ``backoff_base=0.0`` so exponential backoff does not actually
sleep. Stubbing happens at the transport level only — no patching of client
internals — matching the MITECO/ORS client tests.
"""

import json

import httpx
import pytest

from app.infrastructure.external.tomtom import (
    TomTomClient,
    TomTomError,
    TomTomRateLimitError,
    TomTomTimeoutError,
)

USER = (39.47, -0.376)  # Valencia
DESTINATIONS = [(39.48, -0.37), (39.49, -0.36)]


def _build_mock_client(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url="https://tomtom.test")


def _cell(origin_index: int, destination_index: int, length_m: int, time_s: int,
          traffic_s: int | None = 0) -> dict[str, object]:
    summary: dict[str, object] = {
        "lengthInMeters": length_m,
        "travelTimeInSeconds": time_s,
    }
    if traffic_s is not None:
        summary["trafficDelayInSeconds"] = traffic_s
    return {
        "originIndex": origin_index,
        "destinationIndex": destination_index,
        "routeSummary": summary,
    }


def _matrix_body(cells: list[dict[str, object]]) -> bytes:
    return json.dumps(
        {
            "data": cells,
            "statistics": {"totalCount": len(cells), "successes": len(cells), "failures": 0},
        }
    ).encode()


# ── happy path ───────────────────────────────────────────────────────────────


async def test_matrix_parses_summaries_and_builds_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["key"] = request.url.params.get("key")
        captured["body"] = json.loads(request.content)
        body = _matrix_body([_cell(0, 0, 4200, 480, 60), _cell(0, 1, 7500, 900, 0)])
        return httpx.Response(200, content=body)

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
            results = await tomtom.matrix(origin=USER, destinations=DESTINATIONS)
    finally:
        await mock_client.aclose()

    # Request: correct path, key in query, TomTom-shaped body.
    assert captured["path"] == "/routing/matrix/2"
    assert captured["key"] == "fake"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["origins"] == [{"point": {"latitude": 39.47, "longitude": -0.376}}]
    assert len(body["destinations"]) == 2
    assert body["destinations"][0] == {"point": {"latitude": 39.48, "longitude": -0.37}}
    assert body["options"] == {
        "departAt": "now",
        "routeType": "fastest",
        "traffic": "live",
        "travelMode": "car",
    }

    # Response: parsed, ordered, traffic delay surfaced.
    assert len(results) == 2
    assert results[0] is not None and results[1] is not None
    assert results[0].length_in_meters == 4200
    assert results[0].travel_time_in_seconds == 480
    assert results[0].traffic_delay_in_seconds == 60
    assert results[1].length_in_meters == 7500
    assert results[1].traffic_delay_in_seconds == 0


async def test_matrix_orders_results_by_destination_index() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        # Cells returned out of order; client must reorder by destinationIndex.
        return httpx.Response(200, content=_matrix_body([
            _cell(0, 1, 7500, 900),
            _cell(0, 0, 4200, 480),
        ]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
            results = await tomtom.matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert results[0] is not None and results[0].length_in_meters == 4200
    assert results[1] is not None and results[1].length_in_meters == 7500


async def test_matrix_missing_cell_yields_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        # Only destination 0 routed; destination 1 failed (no cell).
        return httpx.Response(200, content=_matrix_body([_cell(0, 0, 4200, 480)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
            results = await tomtom.matrix(USER, DESTINATIONS)
    finally:
        await mock_client.aclose()

    assert results[0] is not None
    assert results[1] is None


async def test_empty_destinations_returns_empty_without_calling_api() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("API must not be called for empty destinations")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
            assert await tomtom.matrix(USER, []) == []
    finally:
        await mock_client.aclose()


# ── retries ──────────────────────────────────────────────────────────────────


async def test_retries_on_503_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, content=_matrix_body([_cell(0, 0, 100, 60)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0) as tomtom:
            results = await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()

    assert calls["n"] == 3
    assert results[0] is not None and results[0].length_in_meters == 100


async def test_retries_on_429_with_retry_after_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, text="Too Many Requests")
        return httpx.Response(200, content=_matrix_body([_cell(0, 0, 100, 60)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0) as tomtom:
            results = await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()

    assert calls["n"] == 2
    assert results[0] is not None


async def test_invalid_retry_after_falls_back_to_backoff() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "soon"}, text="rate limited")
        return httpx.Response(200, content=_matrix_body([_cell(0, 0, 100, 60)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0) as tomtom:
            results = await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()

    assert calls["n"] == 2
    assert results[0] is not None


async def test_429_after_retries_raises_rate_limit_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(
            api_key="fake", client=mock_client, max_retries=2, backoff_base=0.0
        ) as tomtom:
            with pytest.raises(TomTomRateLimitError, match="rate limit"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()


async def test_503_after_retries_raises_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(
            api_key="fake", client=mock_client, max_retries=1, backoff_base=0.0
        ) as tomtom:
            with pytest.raises(TomTomError, match="TomTom request failed"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()


# ── timeout handling ───────────────────────────────────────────────────────────


async def test_timeout_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, content=_matrix_body([_cell(0, 0, 100, 60)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0) as tomtom:
            results = await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()

    assert calls["n"] == 2
    assert results[0] is not None


async def test_timeout_after_retries_raises_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(
            api_key="fake", client=mock_client, max_retries=1, backoff_base=0.0
        ) as tomtom:
            with pytest.raises(TomTomTimeoutError, match="timed out"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()


async def test_connect_error_not_retried_wrapped_as_client_error() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("no route", request=request)

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0) as tomtom:
            with pytest.raises(TomTomError, match="TomTom request failed"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()

    assert calls["n"] == 1  # connect errors are not retried


# ── error / edge cases ─────────────────────────────────────────────────────────


async def test_non_retryable_4xx_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client, backoff_base=0.0) as tomtom:
            with pytest.raises(TomTomError, match="TomTom request failed"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()


async def test_invalid_json_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
            with pytest.raises(TomTomError, match="Could not parse"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()


async def test_malformed_summary_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        # routeSummary missing the required lengthInMeters field.
        body = json.dumps({"data": [{"originIndex": 0, "destinationIndex": 0,
                                      "routeSummary": {"travelTimeInSeconds": 60}}]}).encode()
        return httpx.Response(200, content=body)

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
            with pytest.raises(TomTomError, match="Could not parse"):
                await tomtom.matrix(USER, [(39.48, -0.37)])
    finally:
        await mock_client.aclose()


async def test_missing_api_key_raises() -> None:
    client = TomTomClient(api_key=None)
    with pytest.raises(TomTomError, match="TOMTOM_API_KEY"):
        async with client:
            pass


async def test_calling_without_context_manager_raises() -> None:
    client = TomTomClient(api_key="fake")
    with pytest.raises(TomTomError, match="not initialised"):
        await client.matrix(USER, [(39.48, -0.37)])


async def test_external_client_is_not_closed_on_exit() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_matrix_body([_cell(0, 0, 100, 60)]))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    async with TomTomClient(api_key="fake", client=mock_client) as tomtom:
        await tomtom.matrix(USER, [(39.48, -0.37)])

    assert not mock_client.is_closed
    await mock_client.aclose()
