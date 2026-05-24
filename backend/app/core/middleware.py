"""HTTP request-logging + metrics middleware.

Tags every request with a per-hop ``request_id`` and a cross-service
``correlation_id`` (adopted from an inbound ``X-Correlation-ID`` /
``X-Request-ID`` header when present), so nested service logs trace back to the
originating call. Emits one structured completion log per request with timing,
status, client IP and user-agent, elevating slow requests to WARNING, and
records Prometheus request count / latency / in-flight / exception metrics
labelled by the matched route template.

Unhandled exceptions are logged with full traceback before being re-raised so
FastAPI's exception handlers still produce the response.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import correlation_id_ctx, request_id_ctx
from app.core.metrics import (
    http_exceptions_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    route_template,
)

log = logging.getLogger("app.http")

_UA_MAX_LEN = 200


def _client_ip(request: Request) -> str:
    """Best-effort client IP — first X-Forwarded-For hop, else the socket peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "-"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log + measure every HTTP request: timing, status, ids, Prometheus metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        rid = uuid.uuid4().hex[:8]
        incoming = request.headers.get("x-correlation-id") or request.headers.get(
            "x-request-id"
        )
        cid = incoming or rid
        rid_token = request_id_ctx.set(rid)
        cid_token = correlation_id_ctx.set(cid)
        start = time.perf_counter()

        method = request.method
        path = request.url.path
        query = request.url.query
        qs = f"?{query}" if query else ""
        client_ip = _client_ip(request)
        user_agent = request.headers.get("user-agent", "-")[:_UA_MAX_LEN]

        # A /metrics scrape must not pollute its own timeseries.
        record_metrics = settings.metrics_enabled and path != "/metrics"
        if record_metrics:
            http_requests_in_progress.inc()

        try:
            try:
                response = await call_next(request)
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1000
                route = route_template(request)
                if record_metrics:
                    http_exceptions_total.labels(method=method, route=route).inc()
                    http_requests_total.labels(
                        method=method, route=route, status="500"
                    ).inc()
                    http_request_duration_seconds.labels(
                        method=method, route=route
                    ).observe(elapsed_ms / 1000)
                log.exception(
                    "%s %s%s → 500 (%.1fms) UNHANDLED",
                    method,
                    path,
                    qs,
                    elapsed_ms,
                    extra={
                        "http_method": method,
                        "http_path": path,
                        "http_status": 500,
                        "duration_ms": round(elapsed_ms, 1),
                        "client_ip": client_ip,
                        "user_agent": user_agent,
                    },
                )
                raise

            elapsed_ms = (time.perf_counter() - start) * 1000
            route = route_template(request)
            if record_metrics:
                http_requests_total.labels(
                    method=method, route=route, status=str(response.status_code)
                ).inc()
                http_request_duration_seconds.labels(
                    method=method, route=route
                ).observe(elapsed_ms / 1000)

            slow = elapsed_ms > settings.slow_request_ms
            # 4xx/5xx and slow requests surface at WARNING (visible without DEBUG).
            level = (
                logging.WARNING
                if response.status_code >= 400 or slow
                else logging.INFO
            )
            log.log(
                level,
                "%s %s%s → %d (%.1fms)%s",
                method,
                path,
                qs,
                response.status_code,
                elapsed_ms,
                " SLOW" if slow else "",
                extra={
                    "http_method": method,
                    "http_path": path,
                    "http_status": response.status_code,
                    "duration_ms": round(elapsed_ms, 1),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "slow": slow,
                },
            )
            response.headers["X-Request-ID"] = rid
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            if record_metrics:
                http_requests_in_progress.dec()
            correlation_id_ctx.reset(cid_token)
            request_id_ctx.reset(rid_token)
