# Data Fuel ⛽

> **Find the cheapest gas station — not by price per liter, but by total refuelling cost.**
> A full-stack app that combines real-time Big Data from the Spanish MITECO API with AI price prediction to answer a simple question: *where should I actually drive to fill up?*

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%20async-D71F00" alt="SQLAlchemy 2.0" />
  <img src="https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikitlearn&logoColor=white" alt="scikit-learn" />
  <img src="https://img.shields.io/badge/tests-94%20passing-brightgreen" alt="94 tests passing" />
  <img src="https://img.shields.io/badge/coverage-89%25-brightgreen" alt="Coverage 89%" />
  <img src="https://img.shields.io/badge/mypy-strict-blue" alt="mypy strict" />
  <img src="https://img.shields.io/badge/license-PolyForm%20NC%201.0-lightgrey" alt="License" />
</p>

<!-- IMAGE: hero screenshot — main app view (search form + results) — place a wide screenshot here -->
<p align="center">
  <img src="docs/images/hero.png" alt="Data Fuel — main view" width="800" />
</p>

---

## Why this project

Most fuel apps sort by price per liter and stop there. But driving 15 km to save 3 cents per liter on a 40 L fill-up is a **loss**. Data Fuel solves the actual optimisation problem:

$$
C_i = (V \cdot P_i) + (D_i \cdot K)
$$

| Variable | Meaning |
|---|---|
| `V`  | Litres to refuel (user input) |
| `Pᵢ` | Fuel price at station *i* (€/L) |
| `Dᵢ` | Distance to station *i* (km, haversine) |
| `K`  | Vehicle cost per km (default 0.13 €/km) |

On top of this, a **scikit-learn Ridge regression** predicts the 48-hour price direction per station and suggests *"wait"* or *"refuel now"* based on the expected delta.

---

## Highlights

- **Clean Architecture backend** — strict dependency direction (`domain → services → repositories → infrastructure → API`). No ORM leaks into domain, no HTTP into business logic.
- **Async end-to-end** — FastAPI + SQLAlchemy 2.0 async + `httpx.AsyncClient`. Sync job runs on APScheduler without blocking the event loop.
- **Typed end-to-end** — `mypy --strict` on the backend, `tsc --strict` + `exactOptionalPropertyTypes` + `noUncheckedIndexedAccess` on the frontend. Zero `any` leaking into public signatures.
- **94 tests, 89% coverage** — unit tests for domain logic, integration tests hitting a real in-memory SQLite via ASGI transport, repo-level tests for SQL behaviour. 25 frontend tests covering components, hooks, and API clients.
- **Real data source** — the official Spanish MITECO carburantes API (not web scraping), refreshed hourly via APScheduler with idempotent upserts.
- **ML pipeline** — a `Pipeline` with `ColumnTransformer` (numerical scaling + one-hot encoding) + `Ridge` regression, trained on 30 days of price history with 6-hour per-fuel-type caching.
- **Hardened** — per-endpoint rate limiting (slowapi), CORS allow-list from env, docs endpoints gated behind `DEBUG`, TLS verification via `truststore`, parameterised queries throughout.

---

## Screenshots

<!-- IMAGE: search form — input card with location picker, fuel selector, liters, km cost -->
<table>
  <tr>
    <td align="center"><strong>Search form</strong><br/>
      <img src="docs/images/search-form.png" alt="Search form" width="380" />
    </td>
    <td align="center"><strong>Results + map</strong><br/>
      <img src="docs/images/results-map.png" alt="Ranked results and Leaflet map" width="380" />
    </td>
  </tr>
  <tr>
    <td align="center"><strong>Price history (expanded card)</strong><br/>
      <img src="docs/images/price-history.png" alt="Recharts price history chart" width="380" />
    </td>
    <td align="center"><strong>Prediction badge</strong><br/>
      <img src="docs/images/prediction.png" alt="Prediction badge with AI advice" width="380" />
    </td>
  </tr>
</table>

<!-- IMAGE: favorites filter — shows the heart toggle + filter pill -->
<p align="center">
  <img src="docs/images/favorites.png" alt="Favorites filter" width="600" />
</p>

---

## Architecture

Clean Architecture with strict layering. Arrows represent dependencies (the inner layers know nothing about the outer ones).

```mermaid
flowchart LR
    subgraph Client["Frontend — React + Vite"]
        UI[UI Components<br/>shadcn/ui + Tailwind]
        State[Zustand store<br/>persisted to localStorage]
        Query[TanStack Query<br/>cache + retries]
        UI --> State
        UI --> Query
    end

    subgraph API["Backend — FastAPI"]
        Routes[API layer<br/>routers + Pydantic schemas]
        Services[Domain services<br/>cost_calculator · prediction_service]
        Repos[Repositories<br/>SQLAlchemy 2.0 async]
        DB[(SQLite<br/>stations + price_history)]
        Miteco[MitecoClient<br/>httpx + truststore TLS]
        Scheduler[APScheduler<br/>hourly sync]
    end

    Ext[(MITECO public API<br/>sedeaplicaciones.minetur.gob.es)]

    Query -- HTTPS --> Routes
    Routes --> Services
    Services --> Repos
    Repos --> DB
    Scheduler --> Miteco
    Miteco --> Ext
    Miteco --> Repos
```

Request flow for the core endpoint `GET /api/v1/recommendations`:

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant R as FastAPI router
    participant RL as slowapi limiter
    participant S as cost_calculator
    participant DB as Station repo / SQLite

    U->>F: Enter location + litres
    F->>R: GET /recommendations?lat&lon&liters&fuel_type
    R->>RL: check IP quota (10/min)
    RL-->>R: allow
    R->>DB: list_all stations (optional filters)
    DB-->>R: stations with prices
    R->>S: rank_stations(haversine + cost formula)
    S-->>R: top N ranked by total_cost
    R-->>F: list[RecommendationOut]
    F->>U: render ranked cards + Leaflet map
```

---

## Tech stack & rationale

| Concern | Choice | Why |
|---|---|---|
| Backend framework | **FastAPI** | Async, native Pydantic v2, auto OpenAPI, typed by default |
| ORM | **SQLAlchemy 2.0 async** | Typed API, async driver, upsert helpers, mature migration story (Alembic) |
| DB | **SQLite (aiosqlite)** | Single-file, zero ops, enough write throughput for hourly MITECO sync. Trivially swappable to Postgres via `DATABASE_URL` |
| Scheduling | **APScheduler** | Lightweight, no Redis/Celery dependency for a job that runs hourly |
| ML | **scikit-learn** (`Pipeline` + `Ridge`) | Deterministic, explainable, fast to retrain, no GPU. Trained lazily and cached 6 h per fuel type |
| HTTP client | **httpx + truststore** | Async, uses OS trust store (Windows-friendly, no bundled CAs drift) |
| Rate limiting | **slowapi** | FastAPI-native, IP-keyed, in-memory for dev, pluggable storage for prod |
| Frontend | **React 18 + Vite + TypeScript** | Fast HMR, strict TS config, modern JSX transform |
| Styling | **Tailwind + shadcn/ui** | Utility-first with accessible Radix primitives |
| Data fetching | **TanStack Query** | Cache, dedupe, `enabled` flag for lazy charts, retries, stale-while-revalidate |
| State | **Zustand** (persisted) | Small footprint, selector-based subscriptions, `persist` middleware for favourites/settings |
| Maps | **Leaflet + react-leaflet** | OSM tiles, no API key, lightweight |
| Charts | **Recharts** | SVG, responsive, first-class React API |

---

## Features

### Core
- **Cost ranking** — haversine distance + the cost formula above, with configurable `K`, max distance, and result limit.
- **Real-time data** — hourly upsert from MITECO keeps station metadata and current prices fresh; every sync also appends a row to `price_history` for ML training and charting.
- **Interactive map** — Leaflet markers for every ranked station, centred on the user.
- **Price history** — per-station chart (lazy-fetched only when the card is expanded, avoiding N requests on load).

### AI / ML
- **Training features** — hour-of-day, day-of-week, brand, province.
- **Model** — `ColumnTransformer` (StandardScaler + OneHotEncoder) → `Ridge(alpha=1.0)`.
- **Caching** — one trained pipeline per `FuelType`, TTL 6 h.
- **Output** — predicted price at +48 h, percentage change, Spanish-language advice (`"Espera, el precio bajará…"` / `"Reposta ahora…"`), and the model's R² so users can see confidence.

### UX
- **Favourites** — heart toggle per station, persisted in `localStorage` via Zustand's `persist` middleware, plus a pill to filter results by favourites only.
- **Skeleton loaders** — mirrored-layout skeletons during fetch, no jumpy spinner.
- **Location picker** — geolocation API with graceful fallback to manual coords.
- **Health badge** — live backend status indicator in the header.

---

## API reference

Base URL (dev): `http://localhost:8000/api/v1`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness + version |
| `GET` | `/stations` | List stations, filter by `province` / `municipality` |
| `GET` | `/stations/{id}` | Single station |
| `GET` | `/stations/{id}/price-history/{fuel_type}?days=30` | Price history for charting |
| `GET` | `/recommendations?lat&lon&liters&fuel_type&...` | Ranked stations by total cost |
| `GET` | `/predictions/{station_id}/{fuel_type}` | 48-hour price prediction + advice |

Full OpenAPI is available at `/docs` (Swagger UI) and `/redoc` when `DEBUG=true`.

---

## Project structure

```
datafuel-main/
├── backend/
│   ├── app/
│   │   ├── api/v1/               # Routers + Pydantic schemas
│   │   ├── core/                 # Settings, lifespan, scheduler, rate_limit
│   │   ├── domain/               # Entities + pure services (cost_calculator, prediction_service)
│   │   ├── infrastructure/
│   │   │   ├── database/         # SQLAlchemy models, session, base
│   │   │   └── external/miteco/  # MITECO HTTP client + Pydantic schemas
│   │   ├── repositories/         # Station / price repositories
│   │   └── services/             # sync_service (orchestrates MITECO → DB)
│   ├── tests/
│   │   ├── unit/                 # Pure logic, fixtures only
│   │   └── integration/          # ASGI + in-memory SQLite
│   └── pyproject.toml            # ruff · mypy · pytest · coverage config
└── frontend/
    ├── src/
    │   ├── components/ui/        # shadcn/ui primitives
    │   ├── features/             # recommendations · predictions · price-history · favorites · location · health
    │   ├── pages/                # Home
    │   ├── stores/               # Zustand settings store (persisted)
    │   ├── lib/                  # api-client, utils
    │   └── types/                # Shared enums (FuelType)
    ├── vite.config.ts            # Proxy /api → :8000, Vitest config
    └── package.json
```

---

## Running locally

### Prerequisites
- Python ≥ 3.11
- Node ≥ 20

### Backend

```bash
cd datafuel-main/backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example ../.env      # adjust if needed
uvicorn app.main:app --reload   # http://localhost:8000
```

On startup the app:
1. Creates DB tables (`Base.metadata.create_all`)
2. Optionally runs a MITECO sync (controlled by `SYNC_ON_STARTUP`)
3. Starts the hourly APScheduler job (`SCHEDULER_ENABLED`)

### Frontend

```bash
cd datafuel-main/frontend
npm install
npm run dev                     # http://localhost:5173
```

Vite proxies `/api/*` to `http://localhost:8000`, so CORS is not an issue in development.

---

## Testing & quality

### Backend

```bash
pytest                   # 94 tests, 89% coverage (branch), enforced via --cov-fail-under=80
ruff check app tests     # lint + import order (E, F, I, N, UP, B, A, C4, SIM, RUF)
mypy app                 # strict mode, plugins=[pydantic.mypy]
```

Key choices:
- **Integration tests** use `ASGITransport` + in-memory SQLite. No mocked DB. The test fixture re-creates schema per test for isolation.
- **MITECO client** has a unit test that stubs `httpx` at the transport level — no real network calls in tests.
- `lru_cache` instances (`get_settings`, `get_engine`, `get_session_factory`) are cleared by an `autouse` fixture so env overrides take effect per test.

### Frontend

```bash
npm test        # vitest — 25 tests across 6 files
npm run lint    # eslint (max-warnings 0)
npm run typecheck
npm run build   # tsc -b && vite build
```

- Recharts is module-mocked for jsdom (no real SVG rendering in tests).
- Zustand stores are mocked via `vi.mocked(useStore).mockImplementation((selector) => selector(fakeState))` to keep tests selector-aware.

---

## Security

A quick pass of the threat surface for this app:

| Concern | Mitigation |
|---|---|
| **SQL injection** | Every query goes through SQLAlchemy with bind params. Zero raw SQL. `ilike(f"%{v}%")` still parameterises the argument. |
| **CORS** | Allow-list from `ALLOWED_ORIGINS` env (comma-separated). `allow_credentials=True` is safe because origins are fixed. |
| **Rate limiting** | slowapi, IP-keyed. 10/min on `/recommendations`, 30/min on `/predictions` (configurable via env). Returns `429` on exhaustion. |
| **Docs exposure** | `/docs`, `/redoc`, `/openapi.json` return `404` unless `DEBUG=true`. |
| **Secrets** | `.env` is gitignored; only public URLs live in `.env.example`. No API keys required for MITECO. |
| **TLS** | MITECO client uses `truststore.SSLContext` so certificate verification follows the OS trust store. |
| **Input validation** | FastAPI `Query(ge=..., le=...)` bounds and `Annotated` types on every user-facing parameter; Pydantic schemas on every response. |
| **Deps audit** | `pip-audit` + `npm audit` run clean on runtime deps (only dev-tool advisories remain). |

---

## Roadmap (built in 9 phases)

<details>
<summary><strong>Click to expand — each phase was shipped with tests, lint-clean, and a conventional commit.</strong></summary>

| # | Phase | Deliverable |
|---|---|---|
| 1 | Repo setup | `pyproject.toml`, `package.json`, `.env.example`, `.gitignore`, ruff/mypy/pytest config |
| 2 | Backend skeleton | FastAPI app factory, settings, lifespan, health endpoint |
| 3 | Frontend skeleton | Vite + React + Tailwind + shadcn/ui, routing, `HealthBadge` |
| 4 | Real data | MITECO client with Pydantic schemas, `SyncService`, APScheduler |
| 5 | Core logic | `cost_calculator` with haversine + ranking, `/recommendations` endpoint |
| 6 | Functional frontend | Search form, Zustand settings store, recommendation cards |
| 7 | Visualisations | Leaflet map with station markers |
| 8 | AI predictions | `PredictionService` (Ridge pipeline), `/predictions` endpoint, UI badge |
| 9 | Favourites & polish | Client-side favourites, expandable price-history chart (Recharts, lazy-fetched), skeletons |

</details>

Post-roadmap hardening (security sweep): rate limiting, docs gating, strict type cleanup across backend + frontend.

---

## What I'd do next with more time

- **Deploy** — Fly.io or Railway for the backend, Vercel for the frontend; swap SQLite for managed Postgres.
- **CI** — GitHub Actions matrix for pytest + vitest + ruff + mypy + type-check + build, plus Dependabot and CodeQL.
- **Auth** — real accounts (JWT + refresh) to replace localStorage favourites and enable price alerts via email.
- **Model** — XGBoost with more features (fuel category trends, national averages); evaluate with proper time-series CV.
- **Caching** — Redis for rate-limit storage (so it survives multi-instance deploys) and for the MITECO response.
- **Observability** — structured logging with OpenTelemetry traces, a `/metrics` Prometheus endpoint, and a Grafana dashboard.

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — source available for viewing, **not for commercial use**.

---

## Author

Built by **Joan Oliver** as a portfolio project demonstrating full-stack engineering, clean architecture, async Python, typed React, and applied ML.

- GitHub: [@JoanOliver04](https://github.com/JoanOliver04)
