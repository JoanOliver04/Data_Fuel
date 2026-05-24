"""Prometheus metrics registry — the single catalogue for the whole backend.

Every metric in Data Fuel is defined here against a *dedicated*
:class:`CollectorRegistry` (not the global default) so that:

* tests can read exact values via ``REGISTRY.get_sample_value(...)`` without
  interference from prometheus_client's process-global collectors, and
* nothing else in the process can accidentally register a clashing timeseries.

Instrumentation is deliberately low-overhead: counter/gauge/histogram mutations
are lock-free C-level increments, safe to call from coroutines without ever
awaiting or blocking the event loop. Metric *names* are vendor-neutral
(plain Prometheus exposition), so any Prometheus-compatible scraper works.

Label cardinality is kept bounded on purpose — HTTP routes use the matched
*route template* (never the raw path), and external/provider labels are static
names. Never put user input, ids, or anything secret in a label.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request

# Dedicated registry — see module docstring.
REGISTRY = CollectorRegistry()

# Latency buckets tuned for a JSON API in front of SQLite + occasional external
# routing calls: sub-ms is irrelevant, anything past ~5s is "slow" alike.
_HTTP_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# ── Build info ────────────────────────────────────────────────────────────────
build_info = Gauge(
    "datafuel_build_info",
    "Static build metadata; value is always 1.",
    ["app_name", "version"],
    registry=REGISTRY,
)

# ── HTTP ──────────────────────────────────────────────────────────────────────
http_requests_total = Counter(
    "datafuel_http_requests_total",
    "Total HTTP requests by method, matched route template and status code.",
    ["method", "route", "status"],
    registry=REGISTRY,
)
http_request_duration_seconds = Histogram(
    "datafuel_http_request_duration_seconds",
    "HTTP request latency in seconds by method and route template.",
    ["method", "route"],
    buckets=_HTTP_BUCKETS,
    registry=REGISTRY,
)
http_requests_in_progress = Gauge(
    "datafuel_http_requests_in_progress",
    "Number of HTTP requests currently being served.",
    registry=REGISTRY,
)
http_exceptions_total = Counter(
    "datafuel_http_exceptions_total",
    "Unhandled exceptions escaping request handling, by method and route.",
    ["method", "route"],
    registry=REGISTRY,
)


# ── Cache ─────────────────────────────────────────────────────────────────────
cache_operations_total = Counter(
    "datafuel_cache_operations_total",
    "In-process cache operations by cache name and result "
    "(hit, miss, set, expiration, invalidation).",
    ["cache", "result"],
    registry=REGISTRY,
)
cache_size = Gauge(
    "datafuel_cache_entries",
    "Current number of live entries per in-process cache.",
    ["cache"],
    registry=REGISTRY,
)


# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler_job_runs_total = Counter(
    "datafuel_scheduler_job_runs_total",
    "APScheduler job runs by job id and outcome (executed, error, missed).",
    ["job", "outcome"],
    registry=REGISTRY,
)
scheduler_job_duration_seconds = Histogram(
    "datafuel_scheduler_job_duration_seconds",
    "APScheduler job execution time in seconds by job id.",
    ["job"],
    buckets=(0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0, 1800.0, 3600.0),
    registry=REGISTRY,
)


def route_template(request: Request) -> str:
    """Return the matched route template (low cardinality) or ``"unmatched"``.

    Starlette resolves the route during ``call_next``; reading
    ``request.scope["route"].path`` after that yields ``"/api/v1/{id}"`` rather
    than ``"/api/v1/42"``, which keeps timeseries cardinality bounded.
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        return path
    return "unmatched"


def render_latest() -> tuple[bytes, str]:
    """Serialise the registry to the Prometheus text exposition format."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
