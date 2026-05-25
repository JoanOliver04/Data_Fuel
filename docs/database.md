# Database (SQLite ⇄ PostgreSQL)

Data Fuel runs on **SQLite** for local dev/CI and **PostgreSQL** in production —
the same async SQLAlchemy code and Alembic migrations target both. The driver is
chosen entirely by `DATABASE_URL`; nothing else changes.

- [Configuration](#configuration)
- [Connection pooling](#connection-pooling)
- [Dialect portability](#dialect-portability)
- [Migrations](#migrations)
- [Indexing strategy](#indexing-strategy)
- [Data migration (SQLite → PostgreSQL)](#data-migration-sqlite--postgresql)
- [Observability](#observability)
- [Local & Docker PostgreSQL](#local--docker-postgresql)
- [Cloud deployment](#cloud-deployment)

## Configuration

```
# Local / CI (default)
DATABASE_URL=sqlite+aiosqlite:///./datafuel.db
# Production
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/datafuel
```

Both use **async drivers** (`aiosqlite`, `asyncpg`). `Settings._normalize_database_url`
upgrades the bare `postgres://` / `postgresql://` URLs that Railway/Render/Heroku
hand out to `postgresql+asyncpg://`, and rejects any non-async scheme at startup.
`Settings.is_postgres` drives all dialect-specific behavior. No secrets in code —
the URL is environment-only.

## Connection pooling

PostgreSQL engines are built with a production-grade pool (`session.py`,
`_engine_kwargs`); SQLite keeps its defaults (StaticPool for `:memory:`, single
file otherwise). Tunable via env:

| Setting | Default | Purpose |
| --- | --- | --- |
| `DB_POOL_SIZE` | 5 | persistent connections per instance |
| `DB_MAX_OVERFLOW` | 10 | extra burst connections |
| `DB_POOL_RECYCLE_SECONDS` | 1800 | recycle before cloud DBs cut idle conns |
| `DB_POOL_TIMEOUT_SECONDS` | 30 | wait for a free connection |
| `DB_CONNECT_TIMEOUT_SECONDS` | 10 | asyncpg connect timeout |
| `DB_STATEMENT_TIMEOUT_MS` | 30000 | per-connection Postgres `statement_timeout` (0 = off) |

`pool_pre_ping=True` discards stale connections before use (cloud DBs cycle them),
preventing the classic "server closed the connection unexpectedly" after idle.

## Dialect portability

SQLite-specific SQL is isolated in `app/infrastructure/database/dialects.py`, so
repositories stay database-agnostic:

- **`time_bucket(col, granularity)`** — `strftime` on SQLite, `to_char` on
  PostgreSQL, producing identical bucket labels (analytics trends).
- **`build_upsert(...)`** — `INSERT … ON CONFLICT DO UPDATE` via the right
  dialect insert (station sync). Plain bulk inserts use generic `insert()`.

Adding a third dialect means extending this one module — repositories and
services don't change.

## Migrations

Alembic (`migrations/env.py`) is async and reads `DATABASE_URL`, so it targets
the live database. Migration history is preserved (0001–0004); all use generic
SQLAlchemy types that render correctly on both dialects, and each table/index
creation is **idempotent** (guarded by an inspector check) because the app runs
`Base.metadata.create_all` then `alembic upgrade head` on startup.

```bash
# apply latest (also runs automatically at app startup)
python -m alembic upgrade head
# create a new revision after model changes
python -m alembic revision -m "describe change"
# inspect / roll back
python -m alembic current
python -m alembic downgrade -1
```

## Indexing strategy

| Index | Columns | Why |
| --- | --- | --- |
| `ix_price_history_station_fuel_time` | station_id, fuel_type, recorded_at | per-station current price + station history |
| `ix_price_history_fuel_time` | fuel_type, recorded_at | analytics trend/comarca/brand scans filter by fuel + time **without** station_id |
| `ix_stations_geo` | latitude, longitude | bbox heatmap / candidate selection |
| stations.brand / municipality / province | single | filtering + brand grouping |
| `ix_alerts_user_enabled` | user_identifier, is_enabled | batch alert sweep + per-user listing |
| `ix_notifications_user_created` | user_identifier, created_at | notification feed |
| `ix_notifications_dedup_created` | dedup_key, created_at | dedup-window lookups |

Composite indexes lead with the column the query filters on equality
(`fuel_type`, `user_identifier`) followed by the range/sort column
(`recorded_at`, `created_at`), so PostgreSQL can use them for both filter and
order. No redundant single-column indexes duplicate a composite's leading column.

## Data migration (SQLite → PostgreSQL)

`scripts/migrate_sqlite_to_postgres.py` copies all tables in FK order, idempotently
(`ON CONFLICT (id) DO NOTHING`), validates row counts per table, and resets the
PostgreSQL identity sequences past the imported ids:

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --source "sqlite+aiosqlite:///./datafuel.db" \
  --target "postgresql+asyncpg://user:pass@host:5432/datafuel"
```

Re-running is safe (skips existing rows). Use `--no-create-schema` when Alembic
already created the target schema.

## Observability

Every query is timed (`datafuel_db_query_duration_seconds`); queries over
`DB_SLOW_QUERY_MS` increment `datafuel_db_slow_queries_total` and log a one-line
warning with the statement. `GET /health/ready` runs `SELECT 1` so orchestrators
get a real DB readiness signal; a DB outage returns `503`, never a crash.

## Local & Docker PostgreSQL

**Docker (recommended):**
```bash
docker compose --profile postgres up -d db
python -m alembic upgrade head            # with DATABASE_URL pointed at it
```
The `db` service (postgres:16-alpine) is profile-gated, so the default stack
stays on SQLite. Point the backend at it with
`DATABASE_URL=postgresql+asyncpg://datafuel:datafuel@db:5432/datafuel`.

**Local install:** create a database, then set `DATABASE_URL` and run
`alembic upgrade head`.

## Cloud deployment

Railway / Render / Fly.io all provision a managed Postgres and inject a
connection string:

1. Add a PostgreSQL plugin/addon — it sets `DATABASE_URL` (often `postgres://…`,
   auto-upgraded to asyncpg).
2. Set the app's other env vars (`ALLOWED_ORIGINS`, LLM keys, …).
3. Run `alembic upgrade head` as a release/predeploy command (or rely on the
   startup `create_all` + `upgrade head`).
4. Optionally seed via the one-off data-migration script from an existing SQLite
   file.

The pool defaults suit a single instance; raise `DB_POOL_SIZE` when running
multiple workers/replicas, keeping `pool_size × instances` under the database's
`max_connections`.
