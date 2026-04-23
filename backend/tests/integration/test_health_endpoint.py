"""Integration tests for the FastAPI app and /api/v1/health endpoint."""

from httpx import AsyncClient


async def test_health_returns_ok(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "version": "0.1.0", "name": "Data Fuel API"}


async def test_openapi_schema_exposes_health(api_client: AsyncClient) -> None:
    response = await api_client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths


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
