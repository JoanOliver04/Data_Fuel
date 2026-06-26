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
    Info,
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
    "(hit, miss, set, expiration, eviction, invalidation).",
    ["cache", "result"],
    registry=REGISTRY,
)
cache_size = Gauge(
    "datafuel_cache_entries",
    "Current number of live entries per in-process cache.",
    ["cache"],
    registry=REGISTRY,
)


# ── Machine learning ──────────────────────────────────────────────────────────
ml_model_info = Info(
    "datafuel_ml_model",
    "Active recommendation model metadata (version, trained_at). One series; "
    "updated in place on (re)load so version labels never accumulate.",
    registry=REGISTRY,
)
ml_model_loaded = Gauge(
    "datafuel_ml_model_loaded",
    "1 when the recommendation model artifact is loaded, else 0.",
    registry=REGISTRY,
)
ml_model_mae = Gauge(
    "datafuel_ml_model_mae", "MAE of the active recommendation model.", registry=REGISTRY
)
ml_model_r2 = Gauge(
    "datafuel_ml_model_r2", "R² of the active recommendation model.", registry=REGISTRY
)
ml_model_loaded_timestamp_seconds = Gauge(
    "datafuel_ml_model_loaded_timestamp_seconds",
    "Unix time of the last successful model (re)load; for computing model age.",
    registry=REGISTRY,
)
ml_model_reloads_total = Counter(
    "datafuel_ml_model_reloads_total",
    "Hot-reload attempts by result (success, failure).",
    ["result"],
    registry=REGISTRY,
)
ml_inference_total = Counter(
    "datafuel_ml_inference_total",
    "Model inference calls by model and result (success, error).",
    ["model", "result"],
    registry=REGISTRY,
)
ml_inference_duration_seconds = Histogram(
    "datafuel_ml_inference_duration_seconds",
    "Model inference latency in seconds by model.",
    ["model"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=REGISTRY,
)
ml_retrain_total = Counter(
    "datafuel_ml_retrain_total",
    "Retraining attempts by terminal status (activated, rejected, failed).",
    ["status"],
    registry=REGISTRY,
)
ml_retrain_duration_seconds = Histogram(
    "datafuel_ml_retrain_duration_seconds",
    "End-to-end retraining duration in seconds.",
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 300.0, 900.0, 1800.0, 3600.0),
    registry=REGISTRY,
)
ml_retrain_dataset_rows = Gauge(
    "datafuel_ml_retrain_dataset_rows",
    "Row count of the dataset used by the most recent retraining attempt.",
    registry=REGISTRY,
)
ml_model_activation_failures_total = Counter(
    "datafuel_ml_model_activation_failures_total",
    "Times a freshly activated model failed to hot-reload and was rolled back.",
    registry=REGISTRY,
)


# ── External providers ────────────────────────────────────────────────────────
external_requests_total = Counter(
    "datafuel_external_requests_total",
    "Outbound requests to external providers by provider (miteco, ors, tomtom) "
    "and outcome (success, error).",
    ["provider", "outcome"],
    registry=REGISTRY,
)
external_request_duration_seconds = Histogram(
    "datafuel_external_request_duration_seconds",
    "Latency of outbound external-provider requests in seconds by provider.",
    ["provider"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)
external_retries_total = Counter(
    "datafuel_external_retries_total",
    "Retry attempts against external providers by provider.",
    ["provider"],
    registry=REGISTRY,
)
external_timeouts_total = Counter(
    "datafuel_external_timeouts_total",
    "Timed-out requests to external providers by provider.",
    ["provider"],
    registry=REGISTRY,
)
routing_fallbacks_total = Counter(
    "datafuel_routing_fallbacks_total",
    "Times a routing provider fell back to haversine, by provider.",
    ["provider"],
    registry=REGISTRY,
)
tomtom_quota_used = Gauge(
    "datafuel_tomtom_quota_used",
    "TomTom routing requests consumed in the current UTC day.",
    registry=REGISTRY,
)
tomtom_quota_limit = Gauge(
    "datafuel_tomtom_quota_limit",
    "Configured TomTom daily routing request limit.",
    registry=REGISTRY,
)


# ── AI assistant (LLM) ────────────────────────────────────────────────────────
ai_requests_total = Counter(
    "datafuel_ai_requests_total",
    "AI explanation requests by kind (recommendation, prediction, trend, chat) "
    "and result (llm, fallback, cached).",
    ["kind", "result"],
    registry=REGISTRY,
)
ai_generation_duration_seconds = Histogram(
    "datafuel_ai_generation_duration_seconds",
    "LLM generation latency in seconds by kind.",
    ["kind"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 8.0, 15.0),
    registry=REGISTRY,
)
ai_provider_failures_total = Counter(
    "datafuel_ai_provider_failures_total",
    "LLM provider failures by provider and reason (timeout, http, transport, parse).",
    ["provider", "reason"],
    registry=REGISTRY,
)
ai_cache_operations_total = Counter(
    "datafuel_ai_cache_operations_total",
    "AI explanation cache operations by result (hit, miss).",
    ["result"],
    registry=REGISTRY,
)
ai_fallbacks_total = Counter(
    "datafuel_ai_fallbacks_total",
    "Times the deterministic fallback explanation was used, by kind.",
    ["kind"],
    registry=REGISTRY,
)
ai_hallucination_rejections_total = Counter(
    "datafuel_ai_hallucination_rejections_total",
    "LLM outputs rejected by the safety/validation layer, by reason.",
    ["reason"],
    registry=REGISTRY,
)
ai_tokens_total = Counter(
    "datafuel_ai_tokens_total",
    "LLM tokens consumed by kind and type (prompt, completion), when reported.",
    ["kind", "type"],
    registry=REGISTRY,
)


# ── Analytics ─────────────────────────────────────────────────────────────────
analytics_requests_total = Counter(
    "datafuel_analytics_requests_total",
    "Analytics endpoint requests by endpoint and result (ok, cached, error).",
    ["endpoint", "result"],
    registry=REGISTRY,
)
analytics_query_duration_seconds = Histogram(
    "datafuel_analytics_query_duration_seconds",
    "Analytics aggregation/query latency in seconds by endpoint.",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)
analytics_cache_operations_total = Counter(
    "datafuel_analytics_cache_operations_total",
    "Analytics cache operations by result (hit, miss).",
    ["result"],
    registry=REGISTRY,
)
analytics_heavy_queries_total = Counter(
    "datafuel_analytics_heavy_queries_total",
    "Analytics queries that scanned more rows than the soft threshold, by endpoint.",
    ["endpoint"],
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


# ── Alerts ──────────────────────────────────────────────────────────────────────
alert_evaluations_total = Counter(
    "datafuel_alert_evaluations_total",
    "Alert evaluations by type and result "
    "(triggered, no_trigger, error, cooldown_suppressed, dedup_suppressed).",
    ["alert_type", "result"],
    registry=REGISTRY,
)
alert_batch_duration_seconds = Histogram(
    "datafuel_alert_batch_duration_seconds",
    "Wall-clock duration of one alert-evaluation batch tick.",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)
alert_notifications_total = Counter(
    "datafuel_alert_notifications_total",
    "Notifications dispatched by channel and result (sent, failed).",
    ["channel", "result"],
    registry=REGISTRY,
)
alert_ai_explanation_failures_total = Counter(
    "datafuel_alert_ai_explanation_failures_total",
    "Times the optional LLM alert-explanation enrichment failed and fell back.",
    registry=REGISTRY,
)


# ── Database ────────────────────────────────────────────────────────────────────
db_query_duration_seconds = Histogram(
    "datafuel_db_query_duration_seconds",
    "SQL query execution latency in seconds (all statements).",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)
db_slow_queries_total = Counter(
    "datafuel_db_slow_queries_total",
    "Queries exceeding the slow-query threshold (DB_SLOW_QUERY_MS).",
    registry=REGISTRY,
)


def route_template(request: Request) -> str:
    """Return the matched route template (low cardinality) or ``"unmatched"``.

    Starlette resolves the route during ``call_next``; reading
    ``request.scope["route"].path`` after that yields ``"/api/v1/{id}"`` rather
    than ``"/api/v1/42"``, which keeps timeseries cardinality bounded.

    Note: whether the resolved route is propagated onto the scope seen by this
    *outer* ``BaseHTTPMiddleware`` is Starlette-version-dependent; ``starlette``
    is pinned in ``pyproject.toml`` to a version that does so.
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        return path
    return "unmatched"


def render_latest() -> tuple[bytes, str]:
    """Serialise the registry to the Prometheus text exposition format."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
