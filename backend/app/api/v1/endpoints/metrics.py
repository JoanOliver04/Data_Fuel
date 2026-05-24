"""Prometheus scrape endpoint.

Mounted at the app root (``GET /metrics``), outside the ``/api/v1`` prefix, by
convention so scrapers find it where they expect. Not part of the public API
schema and not rate-limited.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from starlette.status import HTTP_404_NOT_FOUND

from app.core.config import get_settings
from app.core.metrics import render_latest

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose metrics in Prometheus text exposition format.

    Returns 404 when metrics are disabled, so a disabled deployment looks like
    it simply has no metrics endpoint rather than erroring.
    """
    if not get_settings().metrics_enabled:
        return Response(status_code=HTTP_404_NOT_FOUND)
    data, content_type = render_latest()
    return Response(content=data, media_type=content_type)
