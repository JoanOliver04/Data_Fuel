# Analytics

Data Fuel's analytics layer turns the raw price history into a fuel-market
intelligence API: temporal trends, comarca and brand comparisons, geographic
price density, and executive insights. It is **backend-first** — endpoints
return small, typed, pre-aggregated payloads so any frontend (the upcoming
dashboard included) renders without client-side number crunching.

- [Architecture](#architecture)
- [Aggregation strategy](#aggregation-strategy)
- [Endpoints](#endpoints)
- [Insights & LLM seam](#insights--llm-seam)
- [Caching](#caching)
- [Performance & query optimization](#performance--query-optimization)
- [Observability](#observability)
- [Future scalability](#future-scalability)

## Architecture

```
backend/app/analytics/
├── repositories/   # AnalyticsRepository — windowed, grouped-in-DB SQL
├── services/       # shape rows → DTOs, comarca folding, deltas, insights
├── schemas.py      # thin typed response DTOs
├── insights.py     # deterministic executive one-liners
├── enrich.py       # optional LLM rephrase seam (off by default)
├── comarcas.py     # own municipio→comarca loader
├── cache.py        # short-TTL response cache
└── endpoints.py    # /api/v1/analytics/* router
```

**Isolation:** analytics depends only on `app.core` (config/cache/metrics),
infrastructure (DB session + ORM models, read-only) and the shared `FuelType`
enum + `app.ai` provider abstraction (for the optional seam). It never imports
the recommendation engine, ML inference, routing providers or domain services —
and nothing imports analytics back.

## Aggregation strategy

Every query is **time-windowed and grouped in SQLite**, never pulling raw rows
into Python:

- **Trends** — `GROUP BY strftime(bucket, recorded_at)` (hourly for `24h`, daily
  otherwise) → bounded point count (≤24 or ≤365). Optional `group_by`:
  - `brand` → group by `stations.brand` (top 6 by sample count);
  - `comarca` → group by municipality, then fold to comarca in Python via the
    static map (top 6).
- **Comarcas** — municipality `avg/min/max/count` over the window, folded to
  comarca (sample-count-weighted), with `delta_pct`/`direction` vs the previous
  equal window.
- **Brands** — `avg/min/max` grouped by brand, ranked ascending, with deltas.
- **Heatmap** — current snapshot price per station for a fuel (bbox-filterable,
  capped at `limit`).
- **Overview** — counts + per-fuel snapshot averages + cheapest/dearest comarca.

Region unit `comarca` has no DB column; it is the static `municipio → comarca`
map (`ml/data/comarcas_valencia.json`), folded server-side.

## Endpoints

| Endpoint | Key params | Returns |
| --- | --- | --- |
| `GET /api/v1/analytics/overview` | — | KPIs + per-fuel averages + insight |
| `GET /api/v1/analytics/trends` | `fuel_type`, `range`, `group_by` | series of `{bucket, avg/min/max, count}` |
| `GET /api/v1/analytics/comarcas` | `fuel_type`, `range`, `sort`, `limit` | comarca stats + deltas |
| `GET /api/v1/analytics/brands` | `fuel_type`, `range` | ranked brand stats + deltas |
| `GET /api/v1/analytics/heatmap` | `fuel_type`, bbox, `limit` | price-density points |
| `GET /api/v1/analytics/insights` | `fuel_type`, `range` | headline insight bundle |

`range ∈ {24h, 7d, 30d, 90d, 1y}`, `group_by ∈ {none, brand, comarca}`,
`sort ∈ {price, delta, name}`. Empty datasets return `200` with empty
series/items and a deterministic fallback insight (graceful degradation).
Responses are GZip-compressed (≥1 KB) by the global middleware.

## Insights & LLM seam

Insights are **deterministic** — computed purely from the aggregates
(`source: "deterministic"`), so there is zero hallucination risk and the
dashboard works with no LLM. An optional seam (`enrich.py`) can rephrase an
insight through the existing LLM provider **only when**
`ANALYTICS_LLM_INSIGHTS=true` and a provider is configured; any failure, empty
output, or fabricated number silently keeps the deterministic text. Analytics
never depends on LLM availability.

## Caching

A short-TTL `TTLCache` (`ANALYTICS_CACHE_TTL_SECONDS`, default 300s) keyed by
endpoint + params absorbs dashboard request bursts. Analytics data refreshes on
MITECO sync, so a short window keeps payloads fresh. Cache hits/misses are
recorded as metrics.

## Performance & query optimization

- Aggregation runs in the DB; payloads are bounded (capped buckets, top-N
  series, `limit` on comarcas/heatmap) so the frontend never freezes.
- Joins use the existing `(station_id, fuel_type, recorded_at)` index on
  `price_history`, with `fuel_type` + time as leading filters.
- Heavy scans (> soft threshold of buckets) increment
  `datafuel_analytics_heavy_queries_total` and log a warning.
- Short-TTL cache + GZip compression reduce repeated work and payload size.

## Observability

Metrics (see [observability.md](observability.md)):
`datafuel_analytics_requests_total{endpoint,result}`,
`datafuel_analytics_query_duration_seconds{endpoint}`,
`datafuel_analytics_cache_operations_total{result}`,
`datafuel_analytics_heavy_queries_total{endpoint}`.

## Future scalability

- Swap SQLite for Postgres → add covering indexes on `(fuel_type, recorded_at)`
  and `stations(municipality)`; the grouped queries port unchanged.
- Pre-materialise daily comarca/brand rollups (a scheduled job) for `90d`/`1y`
  ranges to cut scan cost.
- Promote the in-process cache to Redis for multi-instance deploys.
- Add a comarca column / lookup table to push folding into SQL.
