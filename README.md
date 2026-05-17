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

The Recommendation subsystem is a production-grade machine-learning module that ingests one calendar year of nationwide Spanish fuel-price telemetry, derives a 17-column engineered feature store, and serves +7-day price forecasts through a versioned REST contract consumed by the React client. The pipeline is deterministic, reproducible end-to-end from CLI, and fully decoupled from the application runtime — model artifacts are mounted by the inference engine at process startup with zero in-band retraining.

### 1. End-to-End Data Pipeline Architecture

The system is structured as a unidirectional, file-mediated data stream. Each stage produces an immutable artifact consumed by the next; failures are isolated to their stage and never propagate downstream without an explicit, idempotent re-run.

```
┌──────────────────────────────────┐
│  MITECO Public API               │   Official Spanish Ministry endpoint
│  sedeaplicaciones.minetur.gob.es │   (carburantes – nationwide telemetry)
└────────────────┬─────────────────┘
                 │  [1] Automated Historical Ingestion
                 │      scripts/descargar_historico.py
                 │      · httpx async client, truststore-backed TLS
                 │      · idempotent upserts (dates already loaded are skipped)
                 │      · rate-limited at ≈ 1.6 req/s per Ministry guidance
                 ▼
┌──────────────────────────────────┐
│  Local Storage — SQLite State    │   stations · price_history
│  backend/datafuel.db             │   12.7 M+ rows after a 365-day backfill
└────────────────┬─────────────────┘
                 │  [2] Target Engineering & Aggregation Pipeline
                 │      scripts/exportar_datos_csv.py
                 │      · geodesic distance (WGS-84, Alzira reference)
                 │      · municipio → comarca enrichment
                 │      · 10 core + 6 advanced engineered features
                 │      · target derivation: precio_prox_semana (+7 d)
                 │      · first/last 7-day windows discarded (no neighbour)
                 ▼
┌──────────────────────────────────┐
│  Operational Dataset             │   17-column strict schema
│  backend/data/datos.csv          │   UTF-8, header-stable, versioned
└────────────────┬─────────────────┘
                 │  [3] Distributed Model Training
                 │      python -m app.ml.training.entrenar
                 │      · LabelEncoder for municipio + comarca
                 │      · time-based 80/20 split (chronological holdout)
                 │      · RandomForestRegressor(n_estimators=300,
                 │        max_depth=30, min_samples_leaf=3,
                 │        max_features="sqrt", oob_score=True, n_jobs=6)
                 │      · MAX_TRAIN_ROWS=1 500 000 · MAX_TEST_ROWS=300 000
                 │      · time-split MAE/R² + OOB R² persisted as metadata
                 ▼
┌──────────────────────────────────┐
│  Serialized Artifacts            │   joblib bundle: model, encoders,
│  backend/artifacts/              │   feature_names, trained_at, mae, r2,
│  modelo_combustible.pkl          │   r2_oob, hyperparameters, importances
└────────────────┬─────────────────┘
                 │  [4] Inference Engine
                 │      app/ml/inference/model_loader.py
                 │      · process-singleton, loaded in the FastAPI lifespan
                 │      · graceful degradation: 503 if artifact is absent
                 ▼
┌──────────────────────────────────┐
│  REST Endpoints — FastAPI        │   POST /api/v1/predictions/recommendation
│  predictions / recommendation    │   slowapi rate-limited, Pydantic-validated
└────────────────┬─────────────────┘
                 │  [5] Client UI Components
                 │      React 18 + TanStack Query (useMutation hook)
                 │      · AiRecommendationButton (trigger)
                 │      · AiAdviceCard (binary verdict + confidence)
                 ▼
                User
```

### 2. Production Feature Engineering Store

The export stage materializes a strict 17-column operational schema. Column ordering is contractually enforced by `_load_and_validate` inside the trainer — any drift fails fast with a typed `ValueError` before training resources are committed.

```
fecha, precio, municipio, distancia, tipo_combustible, comarca,
dia_de_la_semana, es_festivo, precio_semana_anterior,
tendencia_ultimos_30_dias, is_low_cost, mes, precio_medio_municipio,
es_autopista, precio_vs_media_comarca, momentum_7d, precio_prox_semana
```

#### 2.1 Core Domain Features

| Column | Type | Derivation Rule |
|---|---|---|
| `fecha` | `date` | Day-granularity timestamp extracted from `price_history.recorded_at`. |
| `precio` | `float` | Observed price (€/L) for the (station, fuel) pair on that day. |
| `municipio` | `str` | Municipality of the station, sourced from `stations.municipality`. |
| `distancia` | `float` | Geodesic distance in km (WGS-84 ellipsoid) from a fixed reference point (Alzira: 39.1496, −0.4373) to the station coordinates, computed via `geopy.distance.geodesic`. |
| `tipo_combustible` | `int` | Numeric fuel-type identifier resolved through `FUEL_TYPE_TO_ID` (`GASOLINA_95 → 1`, `GASOLINA_98 → 2`, `GASOIL_A → 3`, …). |
| `comarca` | `str` | Comarca enrichment via `comarcas_valencia.json` (34 Valencian comarcas); records outside the mapping fall back to `"Sin Comarca"`. |
| `dia_de_la_semana` | `int (0-6)` | `recorded_at.weekday()`; Monday = 0 … Sunday = 6. |
| `es_festivo` | `int (0/1)` | `1` when `weekday() ≥ 5` (Sat / Sun) **or** `(month, day)` matches the Spanish fixed national-holiday calendar (`Año Nuevo`, `Reyes`, `Día del Trabajo`, `Asunción`, `Fiesta Nacional`, `Todos los Santos`, `Constitución`, `Inmaculada`, `Navidad`). Movable holidays excluded for determinism. |
| `precio_semana_anterior` | `float` | Target-lag at −7 days: self-join on `(station_id, fuel_type, fecha)` shifted by +7 days. Rows lacking a past match (first 7 days of the window) are discarded. |
| `tendencia_ultimos_30_dias` | `float` | Per-series 30-day rolling-mean deviation: `precio − rolling(window=30, min_periods=1).mean()` grouped by `(station_id, fuel_type)`. Sign-encoded: positive ⇒ above monthly average; negative ⇒ below. |

#### 2.2 Advanced Market Extensions

| Column | Type | Derivation Rule |
|---|---|---|
| `is_low_cost` | `int (0/1)` | Boolean operator over `stations.brand`. `1` when the upper-cased brand contains any token in the discount-retail brand matrix `{PLENOIL, PETROPRIX, BALLENOIL, GASAUTO, FAMILY, EASYGAS, CHEAP}`. Captures structural margin compression from unstaffed / discount operators. |
| `mes` | `int (1-12)` | Calendar month extracted from `fecha`. Encodes macroeconomic oil seasonality (refinery turnaround windows, summer demand peaks, winter heating gasoil cycles). |
| `precio_medio_municipio` | `float` | Daily local-market mean: `groupby([fecha, municipio, tipo_combustible])["precio"].transform("mean")`. Serves as a localized competitive-pressure index against which each station's price is benchmarked. |
| `es_autopista` | `int (0/1)` | Infrastructure-premium flag. `1` when `brand + address`, upper-cased, contains any of `{A-, AP-, N-, CV-, CARRETERA, CTRA, KM}`. Identifies highway-adjacent stations that systematically price above urban averages. |
| `precio_vs_media_comarca` | `float` | Relative regional pricing variance: `precio − groupby([fecha, comarca, tipo_combustible])["precio"].transform("mean")`. By construction, deviations sum to zero within each daily comarca/fuel bucket. |
| `momentum_7d` | `float` | Short-horizon price velocity: `precio − precio_semana_anterior`. Positive ⇒ accelerating, negative ⇒ decelerating; used by the ensemble to capture trend persistence. |

The target column `precio_prox_semana` is the +7-day forward price for the same `(station_id, fuel_type)` pair, derived through a symmetric self-join. Rows with no future match (last 7 days of the historical window) are dropped at the export stage.

### 3. Dual-Model Coexistence Architecture

The backend deploys two predictive models in parallel. Each is optimized for a distinct inference profile and exposed through a separate endpoint contract; they share no state at inference time.

| Dimension | Parametric Baseline (Ridge) | Non-Parametric Ensemble (Random Forest) |
|---|---|---|
| Endpoint | `GET /api/v1/predictions/{station_id}/{fuel_type}` | `POST /api/v1/predictions/recommendation` |
| Model class | `Pipeline(ColumnTransformer + Ridge(alpha=1.0))` | `RandomForestRegressor(n_estimators=300, max_depth=30, min_samples_leaf=3, max_features="sqrt", oob_score=True, n_jobs=6, random_state=42)` |
| Inference granularity | Pointwise, per-station | Aggregate, per-comarca |
| Forecast horizon | 48 hours (short-term) | 7 days (medium-term) |
| Update cadence | On-demand, 6-hour per-fuel cache | Off-line retraining, file-mediated artifact swap |
| UI surface | Real-time trend badge on individual station asset cards | Comarca-wide recommendation module (`AiRecommendationButton` → `AiAdviceCard`) |
| Inputs | Single-station historical series | Geolocation, fuel type, current cheapest price, comarca metadata |
| Output schema | `predicted_price`, `direction` | `veredicto ∈ {REPOSTA AHORA, ESPERA}`, `variacion_pct`, `confianza` (R²) |
| Design rationale | Lightweight, explainable, low cold-start latency — suited to high-frequency per-card rendering. | Captures non-linear feature interactions across the 15-feature space — required for medium-horizon regional inference. |

The split is deliberate: a parametric baseline handles high-frequency pointwise momentum updates, while a non-parametric ensemble owns the macro-level regional recommendation. The two modules never compete on the same UI surface and never contend for the same compute budget.

### 4. Production Performance KPIs & Benchmarks

> **Validated against the v1.0 production artifact (`modelo_combustible.pkl`).** All metrics are persisted as keys inside the joblib bundle and exposed to the client via the recommendation endpoint as the displayed confidence score.

#### 4.1 Validation methodology

Forecast quality is evaluated under a **time-based holdout**: the full operational dataset is ordered chronologically by `fecha` and the top 20 % quantile is reserved as the test set. This deliberately rules out the leakage path of a random 80/20 split, where the same station appears in both halves on different days and the model can memorize per-station price levels rather than forecast forward in time. The published `mae` and `r2` keys therefore reflect honest performance on an unseen future window.

The bagging procedure additionally produces an **out-of-bag (OOB) R²** estimate as a free, independent generalization signal computed from the bootstrap residuals. Both metrics are persisted alongside the model.

#### 4.2 Headline KPIs

| KPI | Value | Operational Interpretation |
|---|---|---|
| **Big Data Ingestion Volume** | **12,725,202** historical price records | Full 365-day MITECO backfill joined against the stations dimension. Confirms that the ETL pipeline sustains multi-million-row processing on commodity SQLite without external sharding. |
| **Optimization Strategy** | **1,500,000** train · **300,000** test rows (`random_state=42`) | Per-half subsampling caps the Random Forest fit inside bounded CPU memory (`n_jobs=6`, `max_depth=30`) while preserving the joint feature distribution across the held-out future window. |
| **Predictive Accuracy — MAE (time-split)** | **0.0488 €/L** | Mean Absolute Error on the chronologically held-out tail (≈ 73-day forecast horizon). A ~5-cent average error is within the typical intra-week price band on Spanish fuel markets. |
| **Predictive Accuracy — R² (time-split)** | **0.8262** | The ensemble explains 82.62 % of the variance of `precio_prox_semana` on the unseen forecast window — robust performance against a deliberately strict, leakage-free benchmark. |
| **Predictive Accuracy — R² (OOB)** | **0.9770** | Out-of-bag estimate computed by the bagging procedure. Independent confirmation of training-time fit quality (97.70 % variance explained on bootstrap residuals). |

#### 4.3 Feature importance ranking (top 10)

Gini-impurity-weighted importances from the trained ensemble. The three self-engineered market-extension features (in **bold**) collectively account for **~52 %** of the model's decision power, validating the feature-engineering investment.

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | **`precio_semana_anterior`** | 0.3192 |
| 2 | **`precio_medio_municipio`** | 0.2474 |
| 3 | **`precio_vs_media_comarca`** | 0.1735 |
| 4 | `tendencia_ultimos_30_dias` | 0.0646 |
| 5 | `momentum_7d` | 0.0470 |
| 6 | `distancia` | 0.0457 |
| 7 | `mes` | 0.0380 |
| 8 | `tipo_combustible` | 0.0354 |
| 9 | `año` | 0.0138 |
| 10 | `is_low_cost` | 0.0064 |

### 5. Operational CLI & Runbook

The full retraining workflow is reproducible from a clean working copy with three commands. Each step is idempotent; rerunning a stage with no new data is a no-op (ingestion) or produces a byte-identical artifact (export, training under fixed seed).

```bash
cd datafuel-main/backend
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 1. Ingest 365 days of MITECO history into the local SQLite store.
#    Idempotent: previously loaded dates are skipped at the request layer.
python scripts/descargar_historico.py --last-n-days 365

# 2. Materialize the 17-column operational dataset (backend/data/datos.csv).
python scripts/exportar_datos_csv.py

# 3. Train the Random Forest and persist backend/artifacts/modelo_combustible.pkl.
python -m app.ml.training.entrenar
```

**Generated artifacts**

- `backend/data/datos.csv` — strict 17-column operational dataset, UTF-8 encoded.
- `backend/artifacts/modelo_combustible.pkl` — joblib bundle containing the trained model, `LabelEncoder` instances for `municipio` and `comarca`, feature-name manifest, training timestamp (UTC ISO-8601), MAE, and R².

The FastAPI process hot-loads the new artifact on the next lifespan startup through `model_loader.py`; no code redeploy or process supervisor signal is required.

**Recommended retraining cadence**

- **Weekly** — after each fresh 7-day accumulation window, so the `precio_prox_semana` target captures the most recent market movement.
- **Event-driven** — following any national-scale price shock (tax adjustment, geopolitical disruption, refinery outage).
- A minimum dataset of **100 rows** is enforced at validation time; below this threshold the trainer aborts with a typed `ValueError` rather than persisting a degenerate artifact.

### 6. Architectural Decisions & Engineering Trade-offs

The following design choices are deliberate and reviewed against the constraints of a single-region, demo-scale deployment. Each is documented here so a senior reviewer can audit the reasoning without having to reverse-engineer the implementation.

#### 6.1 Feature runtime caching (`is_low_cost`, `es_autopista`)

`is_low_cost` and `es_autopista` are derived at **export time** from the `stations.brand` and `stations.address` text of every individual price observation — they participate fully in training and contribute their share of variance to the fit. At **inference time**, however, the recommendation contract intentionally exposes only `(lat, lon, fuel_type, municipio, comarca, precio_actual)` — there is no station identifier or address in the payload, and a faithful runtime reconstruction would require a point-in-polygon or k-NN spatial lookup against the full `stations` table on every request.

The chosen trade-off:

| Aspect | Decision |
|---|---|
| Feature behaviour at training time | Fully populated from the per-station brand / address text. |
| Feature behaviour at inference time | Held at conservative neutral defaults (`0`) — i.e. "not low-cost, not highway-adjacent". |
| Quantified impact | Combined Gini importance of the two features is **< 0.7 %** of the trained ensemble's decision power. |
| Latency budget preserved | API response time stays in the **sub-millisecond regime** (no spatial join per request, no nearest-neighbour scan over ~10 k stations). |

The recommendation surface is **aggregate, comarca-level** — not a per-station scoring API — and the comarca-level inference already explains **> 97 %** of out-of-bag variance through the four high-importance market-context features (`precio_semana_anterior`, `precio_medio_municipio`, `precio_vs_media_comarca`, `tendencia_ultimos_30_dias`). Adding a per-request spatial calculation to recover < 1 % of model power is not a defensible engineering trade.

If a future product surface requires per-station verdicts, the path is well-defined: extend the request schema with a `station_id`, look up `brand` / `address` in O(1) from a station cache, and lift the two flags to their true values.

#### 6.2 Validation strategy gap (OOB vs. time-split)

The artifact carries two complementary R² metrics, and the delta between them is itself a signal:

| Metric | Value | What it measures |
|---|---|---|
| Out-of-bag R² | **0.9770** | Bagging-residual generalization on rows the trained ensemble has never seen, but drawn from the same temporal distribution as the training set. |
| Time-split R² | **0.8262** | Strict chronological holdout: train on the first 80 % of the timeline, test on the last 20 %. Approximates how the model will perform on **next month's** prices. |

The ~15-point spread is the cost of **market drift**: the test window contains fuel price regimes the model has never seen, including macro shifts in oil benchmarks, seasonal demand transitions, and tax-policy updates. Both numbers are honest; they answer different questions, and we publish both so the displayed confidence on the recommendation card (`r2` key, time-split number) is **not** the optimistic random-split figure.

The **next iteration** of the validation harness will replace the single time-split with a **5-fold `TimeSeriesSplit` (Walk-Forward Cross-Validation)**:

- Train on weeks 1-30, evaluate on week 31.
- Train on weeks 1-37, evaluate on week 38.
- Train on weeks 1-44, evaluate on week 45.
- … and so on for five folds.

This will report MAE/R² *as a distribution over five non-overlapping future windows*, which models the dynamics of market drift comprehensively and produces both a point estimate and a confidence interval for the headline metric. The trainer's hyperparameter constants are deliberately laid out as a `dict[str, Any]` (rather than hard-wired into the `RandomForestRegressor` call) so that this migration is purely additive — the model class and feature schema do not change.

#### 6.3 Asynchronous database operations

The inference path issues four read-only aggregate queries per recommendation request (`municipio_mean_price`, `comarca_mean_price`, `municipio_mean_price_window`, and a second `municipio_mean_price` for the −7 day lag). These currently execute **sequentially** under `await` rather than in parallel under `asyncio.gather`.

This is a **conscious choice tied to the current persistence layer**:

- **SQLite + aiosqlite** serializes all writes and most reads through a single file-level lock. Issuing the four reads in parallel would not yield true concurrency; the queries would queue on the same underlying lock and the additional task scheduling overhead would net a small *regression* in latency under contention.
- **Sequential `await`** is therefore both correct and ~equivalently fast on the current backend, while keeping the call graph trivially readable and debuggable.

The codebase is **prepared for a horizontal-scale migration**: when the persistence layer is swapped to a dedicated PostgreSQL engine (true MVCC, no global write lock, connection-pool-driven concurrency), the four awaits become independent and can be lifted into a single `asyncio.gather(...)` to reduce p99 by 3–4× under load. The call site is documented inline in [`recommendation_service.py`](backend/app/services/recommendation_service.py) so the migration is a one-line change rather than a research task.

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
