"""Integration tests for HTTP request metrics recorded by the middleware."""

from httpx import AsyncClient
from starlette.requests import Request

from app.core.metrics import REGISTRY, route_template
from app.main import create_app


def test_route_template_resolves_without_scope_route() -> None:
    # An outer BaseHTTPMiddleware does not always see scope["route"] after
    # call_next (varies by Starlette version / OS event loop). route_template
    # must then re-match the request against the app routes instead of
    # mislabelling the metric "unmatched" — which previously broke the counter
    # on the Linux CI runner while passing on Windows.
    app = create_app()
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": [],
        "app": app,
    }
    assert "route" not in scope
    assert route_template(Request(scope)) == "/api/v1/health"


async def test_request_counter_and_histogram_increment(api_client: AsyncClient) -> None:
    count_labels = {"method": "GET", "route": "/api/v1/health", "status": "200"}
    hist_labels = {"method": "GET", "route": "/api/v1/health"}
    before = REGISTRY.get_sample_value("datafuel_http_requests_total", count_labels) or 0.0

    resp = await api_client.get("/api/v1/health")
    assert resp.status_code == 200

    after = REGISTRY.get_sample_value("datafuel_http_requests_total", count_labels) or 0.0
    assert after == before + 1.0

    hist_count = REGISTRY.get_sample_value(
        "datafuel_http_request_duration_seconds_count", hist_labels
    )
    assert hist_count is not None and hist_count >= 1.0


async def test_metrics_endpoint_is_excluded_from_its_own_counter(
    api_client: AsyncClient,
) -> None:
    await api_client.get("/metrics")
    # The /metrics route never records request metrics for itself.
    assert (
        REGISTRY.get_sample_value(
            "datafuel_http_requests_total",
            {"method": "GET", "route": "/metrics", "status": "200"},
        )
        is None
    )


async def test_metrics_body_lists_http_family(api_client: AsyncClient) -> None:
    await api_client.get("/api/v1/health")
    body = (await api_client.get("/metrics")).text
    assert "datafuel_http_requests_total" in body
    assert "datafuel_http_request_duration_seconds" in body
