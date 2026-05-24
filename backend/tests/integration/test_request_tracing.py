"""Integration tests for request-id / correlation-id tracing headers."""

from httpx import AsyncClient


async def test_response_carries_request_and_correlation_ids(api_client: AsyncClient) -> None:
    resp = await api_client.get("/metrics")
    assert "x-request-id" in resp.headers
    assert "x-correlation-id" in resp.headers
    # With no inbound correlation header, correlation defaults to the request id.
    assert resp.headers["x-correlation-id"] == resp.headers["x-request-id"]


async def test_inbound_correlation_id_is_adopted(api_client: AsyncClient) -> None:
    resp = await api_client.get("/metrics", headers={"X-Correlation-ID": "trace-123"})
    assert resp.headers["x-correlation-id"] == "trace-123"
    # The per-hop request id is still freshly generated (distinct from the trace).
    assert resp.headers["x-request-id"] != "trace-123"
