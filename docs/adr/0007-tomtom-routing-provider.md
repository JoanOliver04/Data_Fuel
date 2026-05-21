# 0007 — TomTom routing provider behind a pluggable abstraction

- **Status:** Accepted
- **Date:** 2026-05-21
- **Deciders:** Data Fuel maintainers

> First ADR recorded for this project; the `0007` number is kept to match the
> integration plan that introduced it.

## Context

`/api/v1/recommendations` ranks stations by total cost = fuel + travel. Travel
cost needs a distance. Until now the only road-distance source was the
OpenRouteService (ORS) Matrix API, selected with `DISTANCE_MODE=DRIVING`, with a
silent fallback to straight-line haversine. ORS gives road distance and
duration but **no live-traffic information**, so the ETA shown to users ignores
congestion — the single biggest source of error in a real "cost to get there"
estimate.

We want traffic-aware ETAs without losing the existing offline/ORS paths, and
without breaking the `/recommendations` wire contract, the 5-minute cache, the
slowapi rate limit, or the haversine pre-ranking that bounds external calls.

## Decision

Introduce a `RoutingProvider` port (`app/services/routing/`) with a single
`matrix(origin, destinations) -> list[RouteLeg]` method and three adapters:

- `HaversineProvider` — straight-line, no I/O, never fails.
- `OrsMatrixProvider` — wraps the existing, unchanged `ORSClient`.
- `TomTomMatrixProvider` — new; wraps a `TomTomClient` for **TomTom Matrix
  Routing v2** (`POST /routing/matrix/2`, `traffic=live`, `departAt=now`).

A factory maps `DISTANCE_MODE` to a provider:

| Mode | Provider |
|---|---|
| `EUCLIDEAN` / `HAVERSINE` | `HaversineProvider` |
| `DRIVING` / `DRIVING_ORS` | `OrsMatrixProvider` (haversine if no key) |
| `DRIVING_TOMTOM` | `TomTomMatrixProvider` (haversine if no key) |

`DRIVING` and `HAVERSINE` are kept as backward-compatible aliases. Each
`RouteLeg` carries `distance_km`, `duration_seconds`, `traffic_delay_seconds`,
`provider` and a `failed` flag; the endpoint maps it back to the existing
`DistanceResult`/`StationCost`, so ranking and the response schema are
unchanged. One additive, nullable field — `traffic_delay_seconds` — was added to
`RecommendationOut`; the ETA reuses the pre-existing `driving_duration_min`.

**Matrix v2, not Calculate Route:** we always evaluate N destinations from one
origin, which Matrix v2 returns in a single request (vs N requests) — a ~5×
quota and latency win. Matrix v2 is summary-only by design, so no geometry is
fetched.

**Graceful degradation in the adapter, not the client:** the `TomTomClient`
only does transport (async `httpx`, retries on 429/502/503/504 + timeouts with
exponential backoff, parsing). The adapter catches every failure and falls back
to haversine per-leg, never raising.

**Quota guard in the adapter:** a process-local daily counter
(`TOMTOM_DAILY_QUOTA_LIMIT`, default 2 400) resets at UTC midnight and
short-circuits to haversine once spent, logging one warning per breach. It is
exposed on `/health` (`tomtom_quota`) when TomTom mode is active. The haversine
pre-ranking (top-N candidates, capped at 100) already bounds each call's size.

## Consequences

**Positive**
- Traffic-aware ETAs and a "+N min tráfico" badge when a TomTom key is set.
- ORS and haversine remain first-class and fully selectable; legacy
  `DISTANCE_MODE=DRIVING` keeps working.
- New providers (e.g. HERE) are now a single adapter + factory branch.
- The endpoint can never fail because of a routing outage or spent quota.

**Negative / costs**
- A second external dependency and API key to manage.
- The quota counter is process-local: with multiple workers each tracks its own
  budget, so the effective ceiling is `limit × workers`. Acceptable for the
  current single-process deployment; a shared store (Redis) would be needed at
  scale.
- A new mode value (`DRIVING_TOMTOM`) the legacy `DistanceService` does not
  understand — but `DistanceService` is no longer used by the endpoint.

**Neutral**
- Fallback chain is **TomTom → haversine**. Chaining ORS as a middle tier
  (TomTom → ORS → haversine) is possible via the same port but was left out to
  keep this change minimal.

## Alternatives considered

- **Google Directions / Distance Matrix** — best data, but requires billing
  from the first request and stricter ToS on caching/displaying results.
  Rejected for a free-tier portfolio project.
- **HERE Routing** — comparable free tier and traffic support. A reasonable
  alternative; TomTom was chosen for its simple single-request Matrix v2 and
  query-param auth. HERE remains easy to add as another adapter.
- **Stay on ORS only** — no traffic awareness; rejected because traffic is the
  main accuracy gap.
- **Replace ORS with TomTom (migration)** — rejected; it would drop a working
  free provider and the offline haversine path, and break backward
  compatibility.

## Future-friendly hooks (not built here)

- `route(origin, destination)` on the port for "show the route on the map".
- `optimize_waypoints(...)` for multi-stop optimisation.
- An ETA-aware cost term (`duration_minutes × time_cost_per_minute`).
- `departAt=<future>` for "best time to leave", pairing with the Ridge
  prediction badge.
