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
  <img src="https://img.shields.io/badge/tests-201%20passing-brightgreen" alt="201 tests passing" />
  <img src="https://img.shields.io/badge/coverage-86%25-brightgreen" alt="Coverage 86%" />
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
- **176 backend + 25 frontend tests, 86% coverage** — unit tests for domain logic, integration tests hitting a real in-memory SQLite via ASGI transport, repo-level tests for SQL behaviour. Frontend tests cover components, hooks, and API clients.
- **Real data source** — the official Spanish MITECO carburantes API (not web scraping), refreshed hourly via APScheduler with idempotent upserts.
- **ML pipeline** — a `Pipeline` with `ColumnTransformer` (numerical scaling + one-hot encoding) + `Ridge` regression, trained on 30 days of price history with 6-hour per-fuel-type caching.
- **Performance pass** — SQL-side bbox/radius prefilter (skips ~10 k row hydration per call), top-N pre-rank by haversine before the ORS Matrix call (~5× cheaper quota), async-safe TTL cache on `/recommendations` (cache hits return in <1 ms), GZip middleware (~70 % smaller JSON), Vite manual chunks + lazy-loaded routes and Recharts.
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
    participant C as TTLCache (5 min)
    participant S as cost_calculator
    participant DB as Station repo / SQLite
    participant ORS as ORS Matrix API

    U->>F: Enter location + litres
    F->>R: GET /recommendations?lat&lon&liters&fuel_type
    R->>RL: check IP quota (10/min)
    RL-->>R: allow
    R->>C: lookup by (lat,lon,radius,fuel,profile,…)
    alt cache hit
        C-->>R: cached response
        R-->>F: list[RecommendationOut]
    else cache miss
        R->>DB: find_candidates (bbox / radius + fuel filter pushed to SQL)
        DB-->>R: candidate stations
        R->>S: pre-rank top N by haversine + price
        S-->>R: top N candidates
        R->>ORS: matrix(top N) — driving distance & duration
        ORS-->>R: per-station distances
        R->>S: final rank with driving cost
        S-->>R: top limit by total_cost
        R->>C: store
        R-->>F: list[RecommendationOut] (gzip-compressed)
    end
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
| Compression | **GZipMiddleware** (`minimum_size=1024`) | ~70 % smaller JSON for ranked-stations and prediction payloads |
| Server cache | **In-process TTLCache** (`asyncio.Lock`, 5 min) | Hot `/recommendations` traffic short-circuits the DB + ORS pipeline; invalidated after every MITECO sync |
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
- **Optional driving distance** — when `DISTANCE_MODE=DRIVING`, the top-N candidates (by haversine cost) go through the OpenRouteService Matrix API for real road distance and duration; otherwise haversine alone is used.
- **Real-time data** — hourly upsert from MITECO keeps station metadata and current prices fresh; every sync also appends a row to `price_history` for ML training and charting.
- **Interactive map** — Leaflet markers for every ranked station, centred on the user.
- **Price history** — per-station chart whose component (~300 KB Recharts) and data are *both* deferred until the user expands a card.

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
│   │   ├── core/                 # Settings, lifespan, scheduler, rate_limit, cache, logging, middleware
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
2. Applies any pending Alembic migrations (`alembic upgrade head`, run in a worker thread so its internal `asyncio.run()` doesn't clash with the lifespan loop)
3. Optionally runs a MITECO sync (controlled by `SYNC_ON_STARTUP`)
4. Starts the hourly APScheduler job (`SCHEDULER_ENABLED`)

### Frontend

```bash
cd datafuel-main/frontend
npm install
npm run dev                     # http://localhost:5173
```

Vite proxies `/api/*` to `http://localhost:8000`, so CORS is not an issue in development.

---

## AI Recommendation System

The **Recomendación IA** feature is a full Big Data → ML → API → UI pipeline trained on **one year of Spanish national fuel price history**. It predicts `precio_prox_semana` (the price of a given station+fuel exactly 7 days ahead) and turns that prediction into a binary, human-readable verdict — `REPOSTA AHORA` or `ESPERA` — surfaced to the user through a single click on the AI recommendation button.

### 1. Data pipeline overview

End-to-end flow, from public API ingestion to a deployable model artifact:

```
┌──────────────────────────┐
│  MITECO public API       │  Spanish Ministry — official fuel prices
│  (sedeaplicaciones…)     │
└────────────┬─────────────┘
             │  descargar_historico.py
             │  • httpx async + truststore TLS
             │  • idempotent upserts (skips dates already in DB)
             │  • rate-limited ~1.6 req/s
             ▼
┌──────────────────────────┐
│  SQLite                  │  stations  +  price_history
│  datafuel.db             │  (12.7 M+ rows after 365-day backfill)
└────────────┬─────────────┘
             │  exportar_datos_csv.py
             │  • geopy.distance.geodesic (WGS-84) vs Alzira reference
             │  • municipio → comarca enrichment (34 Valencian comarcas)
             │  • fuel_type → numeric ID mapping
             │  • feature derivation: es_festivo,
             │    precio_semana_anterior, tendencia_ultimos_30_dias
             │  • target derivation: precio_prox_semana (+7 d self-join)
             │  • drops first-7 and last-7 day windows (no neighbour price)
             ▼
┌──────────────────────────┐
│  backend/data/datos.csv  │  11 columns, strict order (Pizarra B spec)
└────────────┬─────────────┘
             │  entrenar.py  ·  python -m app.ml.training.entrenar
             │  • LabelEncoder for municipio + comarca
             │  • train_test_split 80/20, random_state=42
             │  • RandomForestRegressor(n_estimators=100, n_jobs=-1)
             │  • intelligent subsample to 500 k rows (memory bound)
             │  • metrics: MAE + R² on hold-out set
             ▼
┌──────────────────────────┐
│  modelo_combustible.pkl  │  dict[model, encoders, feature_names,
│  backend/artifacts/      │       trained_at, mae, r2]  via joblib
└────────────┬─────────────┘
             │  model_loader.py — singleton, loaded in FastAPI lifespan
             ▼
┌──────────────────────────┐
│  POST /api/v1/predictions/recommendation
│   → recommendation_service.py  (rebuilds the exact training feature vector)
│   → AiRecommendationButton  → AiAdviceCard (React)
└──────────────────────────┘
```

### 2. Feature engineering (Pizarra B compliance)

The professor's whiteboard B specification mandated three additional behavioural variables on top of the base ones. All three are derived directly inside `exportar_datos_csv.py` so the CSV the trainer consumes is already complete:

| Feature | Type | Derivation |
|---|---|---|
| `es_festivo` | `int (0/1)` | `1` if `recorded_at.weekday() ≥ 5` (Saturday or Sunday) **OR** if `(month, day)` belongs to the Spanish fixed national-holiday calendar (`Año Nuevo`, `Reyes`, `Día del Trabajo`, `Asunción`, `Fiesta Nacional`, `Todos los Santos`, `Constitución`, `Inmaculada`, `Navidad`). Movable holidays (Easter) are deliberately excluded so the mapping stays deterministic and reproducible. |
| `precio_semana_anterior` | `float` | A self-join on the aggregated `(station_id, fuel_type, fecha)` frame, shifted **+7 days**, brings each row the price the same station charged for the same fuel exactly one week earlier. Rows that fall on the first 7 days of the historical window have no past match and are dropped via `dropna`. |
| `tendencia_ultimos_30_dias` | `float` | Per-`(station_id, fuel_type)` rolling 30-day mean computed with pandas `transform(rolling(window=30, min_periods=1).mean())`, then `precio − rolling_mean` gives a signed deviation: positive values mean the station is currently above its monthly average (likely to fall), negative values mean it is below (likely to rise). `min_periods=1` keeps early rows defined from day 1. |

The final 11-column strict order written to `datos.csv` (and enforced by `_load_and_validate` in the trainer) is:

```
fecha, precio, municipio, distancia, tipo_combustible, comarca,
dia_de_la_semana, es_festivo, precio_semana_anterior,
tendencia_ultimos_30_dias, precio_prox_semana
```

### 3. Coexistence architecture — two models, two purposes

The project intentionally ships **two predictive models** rather than replacing the existing one. Each is the right tool for a different question:

| | Ridge regression (legacy, kept) | Random Forest regressor (new) |
|---|---|---|
| Endpoint | `GET /api/v1/predictions/{station_id}/{fuel_type}` | `POST /api/v1/predictions/recommendation` |
| Scope | **Per station**, 48 hours ahead | **Per comarca aggregate**, 7 days ahead |
| Surface | Tendency badge on each station card (auto-loaded) | "Recomendación IA" button + `AiAdviceCard` (user-initiated) |
| Input | A single station's recent price history | User location + fuel type + the current cheapest price |
| Output | `predicted_price`, `direction` | `REPOSTA AHORA` / `ESPERA` veredicto + variation % + confidence |
| Why this split | Lightweight linear model, fast cold-start, explainable — perfect for the per-card badge that must render instantly. | Non-linear ensemble that captures interactions between holiday, distance, comarca, prior-week price and 30-day trend — the heavyweight tool for the headline recommendation. |

This dual-model layout is a deliberate engineering decision: a **linear model for pointwise per-station tendencies, an ensemble for aggregated comarca-level recommendations**. The two never compete on the same screen; they cover complementary scopes.

### 4. Real Big Data metrics

The model was trained on real data, not a toy fixture. Numbers from the latest training run:

| Metric | Value | Meaning |
|---|---|---|
| **Rows processed** by the export pipeline | **12,725,202** | One full year (365 days) of MITECO data joined with the stations table, after temporal-window drops. |
| **Rows used for training** | **500,000** (intelligently subsampled, `random_state=42`) | A `MAX_TRAIN_ROWS` cap keeps the Random Forest fit inside CPU memory on a laptop (`n_jobs=-1` with 12.7 M rows triggers OOM at >2 GB per worker copy). Subsampling at this ratio preserves the joint distribution while keeping training under one minute. |
| **MAE** (mean absolute error on hold-out) | **0.0214 €/L** | On average the model misses the true price 7 days ahead by **just 2 cents per litre** — well below the typical daily fluctuation. |
| **R²** (coefficient of determination) | **0.9567** | The Random Forest explains **95.67 % of the variance** of `precio_prox_semana` on unseen rows. |

These metrics are persisted inside `modelo_combustible.pkl` (`mae` and `r2` keys) so the recommendation endpoint can expose the trained R² to the frontend as a confidence indicator on the verdict card — the user literally sees how much the model trusts itself.

### 5. Quick-start CLI commands

Full reproduction of the training pipeline from a freshly-cloned repo:

```bash
cd datafuel-main/backend
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 1. Backfill 365 days of MITECO history into the local SQLite DB
#    (idempotent; existing dates are skipped, ~1.6 req/s)
python scripts/descargar_historico.py --last-n-days 365

# 2. Export SQLite → backend/data/datos.csv with all 11 Pizarra B columns
python scripts/exportar_datos_csv.py

# 3. Train the Random Forest and persist the artifact
python -m app.ml.training.entrenar
```

Outputs:

- `backend/data/datos.csv` — the training dataset (11 columns, strict order)
- `backend/artifacts/modelo_combustible.pkl` — joblib dict containing the model, both label encoders, feature names, training timestamp, MAE and R²

The FastAPI app picks up the new artifact on the next startup via `model_loader.py`; no code redeploy is needed.

### Visual variants of the verdict card

| Veredicto | Card color | Icon | Meaning |
|-----------|-----------|------|---------|
| **REPOSTA AHORA** | Emerald green | ✓ CheckCircle | Price predicted to rise next week — refuel before it gets more expensive |
| **ESPERA** | Amber | ⏳ Clock | Price predicted to fall next week — wait for a lower price |

### When to retrain

- **Weekly** — after each new 7-day accumulation window so `precio_prox_semana` covers fresh price movements.
- **After a national-level price event** (tax change, geopolitical shock).
- Minimum viable dataset: **100 rows** (enforced at validation time with a clear `ValueError`).

---

## Testing & quality

### Backend

```bash
pytest                   # 176 tests, 86% coverage (branch), enforced via --cov-fail-under=80
ruff check app tests     # lint + import order (E, F, I, N, UP, B, A, C4, SIM, RUF)
mypy app                 # strict mode, plugins=[pydantic.mypy]
```

Key choices:
- **Integration tests** use `ASGITransport` + in-memory SQLite. No mocked DB. The test fixture re-creates schema per test for isolation.
- **MITECO client** has a unit test that stubs `httpx` at the transport level — no real network calls in tests.
- `lru_cache` instances (`get_settings`, `get_engine`, `get_session_factory`) and the in-process `recommendations_cache` are reset by an `autouse` fixture so env overrides and cached responses don't leak across tests.

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

## Performance

A focused optimisation pass moved the hot path off the slow rails. Each change keeps the API contract identical and is covered by tests.

| Layer | Change | Why it matters |
|---|---|---|
| SQL | `StationRepository.find_candidates(fuel_type, bbox, radius_origin)` pushes the bounding-box / radius and the *fuel-availability* filter (`price_<fuel> IS NOT NULL`) into the `WHERE` clause. | Avoids hydrating the full `stations` table (~10 k rows in production) on every `/recommendations` call — the typical city-radius query returns 50–300 rows instead. |
| ORS | When `DISTANCE_MODE=DRIVING`, candidates are first pre-ranked by haversine + price and only the top *N* (capped at 100) are sent to the OpenRouteService Matrix API. | Driving distance ≥ haversine, so the cheapest station is virtually guaranteed to live in the haversine top-N. Cuts ORS quota usage and latency by ~5× in dense areas. |
| Cache | `app/core/cache.TTLCache` — async-safe (`asyncio.Lock`), 5-min TTL — keys every `/recommendations` request by its full param tuple. Invalidated after each `SyncService.run()`. | Same params return in <1 ms instead of triggering the full DB + ORS pipeline. Stale prices are impossible because the sync clears the cache. |
| Wire | `GZipMiddleware(minimum_size=1024)`. | JSON payloads ≥1 KB shrink ~70 %; tiny error/health responses stay uncompressed. |
| Bundle | Vite `manualChunks` splits `react-vendor`, `leaflet`, `recharts`, `radix`, `query`. Routes (`Settings`, `NotFound`) and `PriceHistoryChart` are `React.lazy`-loaded. | Initial JS drops from one ~480 KB chunk to ~310 KB cached vendors + ~85 KB app code. Recharts (~380 KB) only loads when a user expands a price-history card. |

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
| 10 | Performance pass | SQL prefilter, ORS top-N pre-rank, TTL cache + sync invalidation, GZip, Vite manual chunks, lazy routes & lazy chart |

</details>

Post-roadmap hardening sweeps: **security** (rate limiting, docs gating, strict type cleanup), **observability** (request-id middleware + structured logging across backend and frontend), and **performance** (table above).

---

## What I'd do next with more time

- **Deploy** — Fly.io or Railway for the backend, Vercel for the frontend; swap SQLite for managed Postgres.
- **CI** — GitHub Actions matrix for pytest + vitest + ruff + mypy + type-check + build, plus Dependabot and CodeQL.
- **Auth** — real accounts (JWT + refresh) to replace localStorage favourites and enable price alerts via email.
- **Model** — XGBoost with more features (fuel category trends, national averages); evaluate with proper time-series CV.
- **Caching** — promote the in-process `recommendations` cache and the slowapi limiter store to Redis so they survive across multi-instance deploys.
- **Observability** — extend the existing request-id-tagged structured logs with OpenTelemetry traces, a `/metrics` Prometheus endpoint, and a Grafana dashboard.

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — source available for viewing, **not for commercial use**.

---

## Author

Built by **Joan Oliver** as a portfolio project demonstrating full-stack engineering, clean architecture, async Python, typed React, and applied ML.

- GitHub: [@JoanOliver04](https://github.com/JoanOliver04)
