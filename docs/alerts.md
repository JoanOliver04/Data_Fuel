# Intelligent Alerts

Data Fuel's alert system turns the recommendation, prediction and pricing layers
into a **proactive assistant**: users define alerts (price thresholds, cheapest
brand, prediction signals, weekly summaries…) and the scheduler evaluates them in
the background, delivering deduplicated, spam-free notifications with honest,
data-grounded messages.

- [Architecture](#architecture)
- [Alert types](#alert-types)
- [Evaluation engine](#evaluation-engine)
- [Anti-spam: cooldown + dedup](#anti-spam-cooldown--dedup)
- [Notifications](#notifications)
- [AI explanations](#ai-explanations)
- [Endpoints](#endpoints)
- [Observability](#observability)
- [Scalability](#scalability)

## Architecture

```
backend/app/alerts/
├── models/          # AlertORM + NotificationORM (shared Base, migration 0003)
├── repositories/    # async data access (alerts, notifications)
├── schemas/ (.py)   # typed DTOs + strict per-type validation
├── evaluators/      # context (shared per-batch reads) + registry + 8 builtins
├── notifications/   # channel abstraction + deduplicating dispatcher
├── services/        # AlertEvaluationEngine (batch orchestration)
├── enrich.py        # optional LLM message rephrase (off by default)
├── cache.py         # short-TTL cache for rephrased messages
└── endpoints.py     # /api/v1/alerts + /api/v1/notifications
```

**Isolation:** alerts *consume* public outputs — `rank_stations`,
`PredictionService.predict`, `PriceRepository`, the AI provider abstraction —
and never import recommendation/ML/routing internals. Nothing imports alerts
back. Alert failures are contained per-alert and never touch core endpoints.

## Alert types

Eight built-ins, all behind one extensible registry. A new type = a new
evaluator class registered in `evaluators/registry.py`; the engine is untouched.

| Type | Fires when | Requires |
| --- | --- | --- |
| `PRICE_BELOW_THRESHOLD` | cheapest price ≤ target | `threshold_price` |
| `PRICE_CHANGE` | price moved ≥ `threshold_pct` vs 7d ago | `threshold_pct` |
| `FAVORITE_STATION_CHANGE` | a specific station's price changed | `station_id` |
| `CHEAPEST_BRAND` | a brand is cheapest within radius | `brand`, lat/lon |
| `WEEKLY_SUMMARY` | weekly digest (one per ISO week) | — |
| `WAIT_VS_REFUEL_SIGNAL` | predicted drop ≥ `threshold_pct` | `threshold_pct`, lat/lon |
| `PREDICTION_TREND` | forecast move ≥ threshold (default 0.5%) | lat/lon |
| `TOTAL_COST_DROP` | traffic/total cost dropped ≥ `threshold_pct` vs yesterday | `threshold_pct`, lat/lon |

Per-type required fields are validated strictly at creation (`schemas.py`), so an
evaluator never runs on an under-specified alert.

## Evaluation engine

One `run_once` is a batch tick fired by the scheduler (`alert_eval` interval
job). It:

1. loads enabled alerts (capped at `ALERTS_EVAL_BATCH_SIZE`);
2. builds one **`AlertContext`** that memoises shared reads (station list,
   rankings, predictions, history) so a batch over the same fuel/area does the
   work once;
3. evaluates each alert behind its **own `try/except`** — a single failure logs
   structurally, increments a metric, and the batch continues.

**Async safety:** all ORM access is async over one session; the CPU-bound ML
prediction runs in a worker thread (`asyncio.to_thread`), so the event loop is
never blocked. The job is `max_instances=1` + `coalesce=True`, so a slow tick
can never pile up or crash the scheduler.

## Anti-spam: cooldown + dedup

Two independent layers make spam structurally impossible:

- **Cooldown** — an alert within `cooldown_minutes` of its last trigger is
  skipped before evaluation (cheap, also saves work).
- **Deduplication** — each trigger carries a *state signature* (e.g. the rounded
  price). The dispatcher namespaces it (`{alert_id}:{signature}`) and suppresses
  any notification with the same key inside `ALERTS_DEDUP_WINDOW_MINUTES`.

An alert re-notifies only when **both** the cooldown has elapsed **and** the
trigger state actually changed.

## Notifications

A `NotificationChannel` Protocol abstracts delivery; the initial `InAppChannel`
treats persistence as delivery (the stored row *is* the in-app notification).
Email / push / Telegram channels slot in later without touching the dispatcher.
Channels never raise — failures return `False` so delivery stays retry-safe.
History is append-only (`notifications` table).

## AI explanations

The deterministic message is authoritative. With `ALERTS_LLM_EXPLANATIONS=true`
and a provider configured, `enrich.py` may **rephrase** it through the existing
LLM abstraction — but any output that introduces a number not in the original is
rejected, and disabled/failed/parse-error/fabricated cases silently keep the
deterministic text. Rephrasings are cached by message (dedup). Alerts never
depend on the LLM being available.

## Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/alerts` | POST | create alert (strict per-type validation, `max_per_user`) |
| `/api/v1/alerts` | GET | list a user's alerts |
| `/api/v1/alerts/{id}` | PATCH | update mutable fields |
| `/api/v1/alerts/{id}` | DELETE | remove an alert |
| `/api/v1/notifications` | GET | notification feed |

No auth layer exists, so requests are scoped by an explicit `user_identifier`;
cross-user access returns `404`. All routes are rate-limited (`ALERTS_RATE_LIMIT`)
and never run evaluation, so they are cheap and cannot trigger work.

## Observability

Metrics (see [observability.md](observability.md)):
`datafuel_alert_evaluations_total{alert_type,result}` (result ∈ triggered,
no_trigger, error, cooldown_suppressed, dedup_suppressed),
`datafuel_alert_batch_duration_seconds`,
`datafuel_alert_notifications_total{channel,result}`,
`datafuel_alert_ai_explanation_failures_total`. The scheduler job is also tracked
by the existing `datafuel_scheduler_job_*` families.

## Scalability

- Indexed batch sweep (`(user_identifier, is_enabled)`); `ALERTS_EVAL_BATCH_SIZE`
  bounds per-tick work.
- `AlertContext` memoisation collapses duplicate reads within a batch.
- Notifications are append-only with `(user_identifier, created_at)` and
  `(dedup_key, created_at)` indexes; archive/partition old rows when large.
- The interval job is horizontally safe as long as a single scheduler instance
  owns evaluation; multi-instance would add a leased lock or move ticks to a
  queue worker — no evaluator changes needed.
