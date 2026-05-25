"""Production-grade exception handling.

Unhandled exceptions return a sanitised JSON body carrying the request and
correlation ids (so a user-reported error can be tied to server logs) but never
the stack trace or internal message — except in DEBUG, where the exception type
and message are included to speed up local debugging. The full traceback is
always written to the structured logs server-side by the request middleware.
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

log = logging.getLogger("app.errors")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a sanitised 500 response correlated to the originating request."""
    request_id = getattr(request.state, "request_id", "-")
    correlation_id = getattr(request.state, "correlation_id", "-")
    body: dict[str, str] = {
        "detail": "Internal Server Error",
        "request_id": request_id,
        "correlation_id": correlation_id,
    }
    if get_settings().debug:
        body["exception"] = f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content=body)
