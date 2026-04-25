"""HTTP request-logging middleware.

Logs every request as ``METHOD path → status (Xms)`` and tags every log
emitted while the request is in flight with a short correlation id, so
nested service logs can be traced back to the originating HTTP call.

Unhandled exceptions are logged with full traceback before being re-raised
so FastAPI's exception handlers still produce the response.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_ctx

log = logging.getLogger("app.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with timing + status + correlation id."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = uuid.uuid4().hex[:8]
        token = request_id_ctx.set(rid)
        start = time.perf_counter()

        method = request.method
        path = request.url.path
        query = request.url.query

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "%s %s%s → 500 (%.1fms) UNHANDLED",
                method,
                path,
                f"?{query}" if query else "",
                elapsed_ms,
            )
            request_id_ctx.reset(token)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        # 4xx and 5xx surface at WARNING so they're visible without DEBUG.
        level = (
            logging.WARNING
            if response.status_code >= 400
            else logging.INFO
        )
        log.log(
            level,
            "%s %s%s → %d (%.1fms)",
            method,
            path,
            f"?{query}" if query else "",
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = rid
        request_id_ctx.reset(token)
        return response
