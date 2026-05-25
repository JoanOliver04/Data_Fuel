# Observability

Data Fuel ships production-grade observability across the backend: structured
JSON logs with request tracing, Prometheus metrics, and liveness/readiness/
detail health endpoints. Everything is vendor-neutral (plain Prometheus
exposition + stdout JSON), low-overhead, and never blocks the event loop.

- [Quick reference](#quick-reference)
- [Structured logging & request tracing](#structured-logging--request-tracing)
- [Health endpoints](#health-endpoints)
- [Metrics catalogue](#metrics-catalogue)
- [Prometheus setup](#prometheus-setup)
- [Grafana dashboards](#grafana-dashboards)
- [Troubleshooting](#troubleshooting)

## Quick reference

| Concern | Where |
| --- | --- |
| Metrics scrape | `GET /metrics` (Prometheus text; outside `/api/v1`) |
| Liveness | `GET /api/v1/health/live` |
| Readiness | `GET /api/v1/health/ready` (503 when not ready) |
| Detailed status | `GET /api/v1/health/details` |
| Legacy liveness | `GET /api/v1/health` (unchanged contract) |
| Logs | stdout — JSON in production, text in `DEBUG` |
| Request id header | `X-Request-ID` (per hop) |
| Correlation id header | `X-Correlation-ID` (adopted from inbound, else = request id) |

### Configuration

| Setting | Default | Effect |
| --- | --- | --- |
| `METRICS_ENABLED` | `true` | When false, `/metrics` returns 404 and the middleware skips instrumentation. |
| `SLOW_REQUEST_MS` | `1000` | Requests slower than this are logged at WARNING with a `slow` flag. |
| `DEBUG` | `false` | `false` → JSON logs + sanitised errors; `true` → text logs + exception detail in 500s. |
| `LOG_LEVEL` | `INFO` | Root log level (overridden to `DEBUG` when `DEBUG=true`). |

## Structured logging & request tracing

All logs go to stdout via one `setup_logging()` call (`app/core/logging.py`).
In production each line is a single JSON object; in `DEBUG` it's a readable
text line. Never use `print` — always `logging.getLogger(__name__)`.

Every request is tagged with two ids, carried in coroutine-safe `ContextVar`s
and echoed as response headers:

- **`request_id`** — fresh 8-char id per HTTP hop.
- **`correlation_id`** — adopted from an inbound `X-Correlation-ID` or
  `X-Request-ID` header (so a trace survives across services), otherwise equal
  to the request id.

The request middleware emits one completion log per request with method, path,
status, duration, client IP and user-agent. 4xx/5xx **and** slow requests log at
WARNING. Example production log lines (pretty-printed here; real output is one
line each):

```json
{
  "timestamp": "2026-05-25T08:30:01.124+00:00",
  "level": "INFO",
  "service": "datafuel-api",
  "logger": "app.http",
  "message": "GET /api/v1/recommendations → 200 (42.7ms)",
  "request_id": "9f3a1c20",
  "correlation_id": "9f3a1c20",
  "http_method": "GET",
  "http_path": "/api/v1/recommendations",
  "http_status": 200,
  "duration_ms": 42.7,
  "client_ip": "203.0.113.7",
  "user_agent": "Mozilla/5.0 …",
  "slow": false
}
```

```json
{
  "timestamp": "2026-05-25T08:31:14.880+00:00",
  "level": "ERROR",
  "service": "datafuel-api",
  "logger": "app.http",
  "message": "GET /api/v1/recommendations → 500 (5012.3ms) UNHANDLED",
  "request_id": "1b77de04",
  "correlation_id": "trace-from-gateway-42",
  "http_status": 500,
  "duration_ms": 5012.3,
  "exception": "TimeoutError: ORS request timed out"
}
```

Unhandled exceptions return a **sanitised** JSON 500 — `detail`, `request_id`,
`correlation_id` — never a stack trace or internal message (except in `DEBUG`).
The full traceback is always in the server logs, correlated by id.

## Health endpoints

| Endpoint | Purpose | Status codes |
| --- | --- | --- |
| `/api/v1/health/live` | Process is up and serving | 200 |
| `/api/v1/health/ready` | Dependency checks | 200 ready/degraded, 503 not ready |
| `/api/v1/health/details` | Rich operational snapshot | 200 |
| `/api/v1/health` | Legacy liveness (+ TomTom quota) | 200 |

**Readiness** gates only on the database (the one hard dependency). A missing
model, idle scheduler or keyless provider mark the response `degraded`
(still 200) rather than failing the probe — the API can still serve traffic.

```jsonc
// GET /api/v1/health/ready  → 200
{
  "status": "degraded",
  "checks": {
    "database":  { "ok": true },
    "cache":     { "ok": true },
    "model":     { "ok": false, "detail": "model not loaded" },
    "scheduler": { "ok": true }
  }
}
```

`/api/v1/health/details` additionally reports the active model (version,
trained_at, mae, r2), cache size, scheduler jobs + next-run times, last
retraining timestamp, routing provider + TomTom quota, and uptime.

**Kubernetes** probes map directly:

```yaml
livenessProbe:
  httpGet: { path: /api/v1/health/live, port: 8000 }
  periodSeconds: 10
readinessProbe:
  httpGet: { path: /api/v1/health/ready, port: 8000 }
  periodSeconds: 10
```

## Metrics catalogue

All metrics are registered on a dedicated `CollectorRegistry`
(`app/core/metrics.py`) and prefixed `datafuel_`. Labels are kept low-cardinality
(route templates, static provider/job names) — never raw paths, ids, or secrets.

### HTTP
| Metric | Type | Labels |
| --- | --- | --- |
| `datafuel_http_requests_total` | counter | `method`, `route`, `status` |
| `datafuel_http_request_duration_seconds` | histogram | `method`, `route` |
| `datafuel_http_requests_in_progress` | gauge | — |
| `datafuel_http_exceptions_total` | counter | `method`, `route` |

### Machine learning
| Metric | Type | Labels |
| --- | --- | --- |
| `datafuel_ml_model_info` | info | `version`, `trained_at` |
| `datafuel_ml_model_loaded` | gauge | — |
| `datafuel_ml_model_mae` / `_r2` | gauge | — |
| `datafuel_ml_model_loaded_timestamp_seconds` | gauge | — (for model age) |
| `datafuel_ml_model_reloads_total` | counter | `result` |
| `datafuel_ml_inference_total` | counter | `model`, `result` |
| `datafuel_ml_inference_duration_seconds` | histogram | `model` |
| `datafuel_ml_retrain_total` | counter | `status` |
| `datafuel_ml_retrain_duration_seconds` | histogram | — |
| `datafuel_ml_retrain_dataset_rows` | gauge | — |
| `datafuel_ml_model_activation_failures_total` | counter | — |

### External providers & routing
| Metric | Type | Labels |
| --- | --- | --- |
| `datafuel_external_requests_total` | counter | `provider`, `outcome` |
| `datafuel_external_request_duration_seconds` | histogram | `provider` |
| `datafuel_external_retries_total` | counter | `provider` |
| `datafuel_external_timeouts_total` | counter | `provider` |
| `datafuel_routing_fallbacks_total` | counter | `provider` |
| `datafuel_tomtom_quota_used` / `_limit` | gauge | — |

Providers: `miteco`, `ors`, `tomtom`.

### Cache & scheduler
| Metric | Type | Labels |
| --- | --- | --- |
| `datafuel_cache_operations_total` | counter | `cache`, `result` (hit/miss/set/expiration/invalidation) |
| `datafuel_cache_entries` | gauge | `cache` |
| `datafuel_scheduler_job_runs_total` | counter | `job`, `outcome` (executed/error/missed) |
| `datafuel_scheduler_job_duration_seconds` | histogram | `job` |

### Build
`datafuel_build_info{app_name, version}` — static, always 1.

## Prometheus setup

```yaml
# prometheus.yml
scrape_configs:
  - job_name: datafuel-api
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets: ["datafuel-api:8000"]
```

> **Single process only.** The app runs one uvicorn worker per container, so the
> default registry is correct. If you ever scale to multiple workers in one
> process (gunicorn `--workers N`), switch to `prometheus_client`'s
> [multiprocess mode](https://prometheus.github.io/client_python/multiprocess/).

## Grafana dashboards

Useful PromQL starting points:

```promql
# Request rate by route
sum by (route) (rate(datafuel_http_requests_total[5m]))

# p95 latency by route
histogram_quantile(0.95,
  sum by (le, route) (rate(datafuel_http_request_duration_seconds_bucket[5m])))

# 5xx error ratio
sum(rate(datafuel_http_requests_total{status=~"5.."}[5m]))
  / sum(rate(datafuel_http_requests_total[5m]))

# Cache hit rate (recommendations)
sum(rate(datafuel_cache_operations_total{cache="recommendations",result="hit"}[5m]))
  / sum(rate(datafuel_cache_operations_total{cache="recommendations",result=~"hit|miss"}[5m]))

# External provider error rate
sum by (provider) (rate(datafuel_external_requests_total{outcome="error"}[5m]))

# Model age (hours)
(time() - datafuel_ml_model_loaded_timestamp_seconds) / 3600

# TomTom quota utilisation
datafuel_tomtom_quota_used / datafuel_tomtom_quota_limit

# Retrain outcomes (last day)
sum by (status) (increase(datafuel_ml_retrain_total[1d]))
```

Recommended alerts: 5xx ratio > 1% for 5m; readiness 503; model age > 10 days;
`datafuel_ml_model_activation_failures_total` increasing; TomTom quota > 90%.

## Troubleshooting

| Symptom | Look at |
| --- | --- |
| `/metrics` returns 404 | `METRICS_ENABLED=false`. |
| A user reports an error | Grep logs for their `request_id`/`correlation_id` from the 500 body. |
| Endpoint feels slow | `slow=true` WARNING logs + `datafuel_http_request_duration_seconds` p95 by route; check `datafuel_external_request_duration_seconds`. |
| Predictions 503 | `/health/details` → `model.loaded`; `datafuel_ml_model_loaded` should be 1. |
| Routing degraded to straight-line | `datafuel_routing_fallbacks_total` + TomTom quota gauges; check provider API key in `/health/details`. |
| Retrain not happening | `/health/details` → `scheduler.jobs` next-run; `datafuel_scheduler_job_runs_total{job="ml_retrain"}`. |
| Tracing a request across services | Pass the upstream `X-Correlation-ID`; it appears on every log line and the response header. |
