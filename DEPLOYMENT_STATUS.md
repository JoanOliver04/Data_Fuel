# Data Fuel — Deployment Status (demo build)

Prepared for a stable, free, single-instance defense deployment. **No business
logic, ML logic, or API contracts were modified** — only deployment assets and
configuration were added. SQLite is used (PostgreSQL is not required; the data
layer is dialect-portable via [dialects.py](backend/app/infrastructure/database/dialects.py)).

---

## 1. What was changed

### Added (deployment assets / config)
| File | Purpose |
|---|---|
| [backend/scripts/make_demo_slice.py](backend/scripts/make_demo_slice.py) | Reproducible, pure-`sqlite3` utility that builds the demo DB slice. Imports **no** app code. |
| [backend/Dockerfile.demo](backend/Dockerfile.demo) | Self-contained demo image: bakes the slice + trained model, installs the `xai` extra (SHAP). |
| [render.yaml](render.yaml) | Render Blueprint — deploys the **prebuilt** demo image (SQLite, background work off). |
| [netlify.toml](netlify.toml) | Frontend build/publish config + SPA redirect + asset caching. |
| [frontend/public/_redirects](frontend/public/_redirects) | SPA deep-link fallback (`/* → /index.html 200`). |

### Modified
| File | Change |
|---|---|
| [backend/.dockerignore](backend/.dockerignore) | Re-includes `data/datafuel.db` + `artifacts/modelo_combustible.pkl` for the demo build, while still excluding the 2.3 GB root `datafuel.db`. |

### Generated on disk (NOT committed — git-ignored build inputs)
| Artifact | Size | Notes |
|---|---|---|
| `backend/data/datafuel.db` | **210 MB** | 30-day slice (see §2). `*.db` is git-ignored — it is a build input, baked by `docker build`. |
| `backend/artifacts/modelo_combustible.pkl` | **69 MB** | Pre-existing trained Random Forest. `*.pkl` git-ignored — also a build input. |

### Untouched (verified, no diff)
- [backend/Dockerfile](backend/Dockerfile) (production) and [docker-compose.yml](docker-compose.yml) — the production volume-based path is unchanged.
- All `app/` business, ML, and API code.

---

## 2. The SQLite slice

Built with `python scripts/make_demo_slice.py --days 30` from the 2.3 GB / 14.1 M-row source.

| Property | Value |
|---|---|
| Stations | **12,449 (ALL)** — full geographic coverage preserved |
| price_history rows | **1,376,606** |
| Date range | `2026-04-30` → `2026-05-29` |
| File size | **210 MB** (VACUUM-compacted) |
| Other tables | `vehicle_profiles`, `training_runs`, `alerts`, `notifications` created **empty** (none are required for read endpoints; the model loads from the `.pkl`, not from `training_runs`) |

**Why 30 days is sufficient (evidence-based):** the inference feature builder
([recommendation_service.py:178](backend/app/services/recommendation_service.py#L178)) needs only:
- the 30-day municipio trend window (`_TREND_WINDOW_DAYS = 30`), which reads `[today−30, today)` → fully inside the slice for a ~June-1 defense, and
- the 7-day price lag (`today−7` ≈ `2026-05-25`) → present in the slice.

Keeping all stations preserves map/comparison/recommendation coverage; trimming
only the *time depth* of `price_history` is what shrinks 2.3 GB → 210 MB.

---

## 3. Verification (ran the REAL app against the slice)

Booted the actual FastAPI app (`app.main:app`) with its real lifespan (DB init +
model load) against `data/datafuel.db`, model loaded from `artifacts/`, SHAP
available, and hit the **real routes** over ASGI. All passed:

| Capability | Route exercised | Result |
|---|---|---|
| Stations | `GET /api/v1/stations?municipality=Madrid` | ✅ 200 |
| Analytics | `GET /api/v1/analytics/overview` · `GET /api/v1/analytics/trends?fuel_type=gasolina_95&range=30d` | ✅ 200, populated series |
| Recommendation engine | `GET /api/v1/recommendations?lat=…&lon=…&liters=40&fuel_type=gasolina_95` | ✅ 200, ranked list |
| Predictions (model) | `POST /api/v1/predictions/recommendation` | ✅ 200 — `precio_predicho=1.559`, verdict `REPOSTA AHORA`, confidence `0.853` (**real inference, not a neutral fallback**) |
| XAI (global) | `GET /api/v1/xai/global-feature-importance` | ✅ 200 |
| XAI (SHAP local) | `POST /api/v1/xai/explain-recommendation` | ✅ 200 |

The temporary harness used for this was deleted after the run.

> Scope note: this verifies the **app + slice + model + SHAP** stack (the actual
> runtime). The Docker packaging itself (COPY paths, `.[xai]` install) is
> mechanical; a one-time local `docker build` + `docker run` smoke test is listed
> as a manual step in §6 to be 100% certain before the defense.

---

## 4. Final image contents (`backend/Dockerfile.demo`)

```
/app
├── app/                              # application code
├── scripts/                          # operational scripts
├── alembic.ini + migrations/         # so startup `alembic upgrade head` runs clean
├── data/datafuel.db                  # 210 MB — 30-day SQLite slice (BAKED IN)
└── artifacts/modelo_combustible.pkl  #  69 MB — trained model (BAKED IN)
/opt/venv                             # runtime deps incl. xai extra (SHAP/numba/llvmlite)
```
- Base: `python:3.12-slim`, non-root user `datafuel`, virtualenv on PATH.
- Env defaults baked in: `DATABASE_URL=sqlite+aiosqlite:////app/data/datafuel.db`,
  `SYNC_ON_STARTUP=false`, `SCHEDULER_ENABLED=false`, `ALERTS_ENABLED=false`,
  `RETRAIN_ENABLED=false`, `DATAFUEL_LLM_PROVIDER=fallback`, `DISTANCE_MODE=EUCLIDEAN`,
  `DEBUG=false`.
- Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1`
  (binds Render's `$PORT`; single worker is mandatory — model singleton + scheduler).

### Estimated image size
| Layer | Approx. |
|---|---|
| `python:3.12-slim` base | ~150 MB |
| Python deps incl. `.[xai]` (pandas, numpy, scikit-learn, **shap + numba + llvmlite**) | ~700–900 MB |
| Slice DB | 210 MB |
| Model | 69 MB |
| **Total on disk** | **≈ 1.1 – 1.4 GB** (≈ 500–650 MB compressed when pushed) |

This is well within Render's free image limits; the main cost is a slow first
push/pull. The `xai` extra (SHAP) is the biggest single contributor but is
required for the XAI endpoints.

---

## 5. Deployment instructions (overview)

```
Frontend (Netlify, free)            Backend (Render, free)
─────────────────────────           ──────────────────────────────────
base=frontend                       prebuilt image: ghcr.io/<you>/datafuel-backend-demo
build=npm run build                 SQLite slice + model baked in
publish=dist                        ALLOWED_ORIGINS = <netlify-url>
VITE_API_BASE_URL = <render-url> ─────────────────────────►  /api/v1/*
```

---

## 6. Remaining manual steps before Render deployment

> These can't be done from inside the repo prep — they need your registry/host
> accounts and the live URLs. **Why an image, not a Git build:** the slice (210 MB)
> and model (69 MB) are git-ignored and the slice exceeds GitHub's 100 MB per-file
> limit, so Render cannot build them from Git. Build where the files exist, push,
> then deploy the image.

### A. Build + smoke-test the image locally
```bash
cd backend
docker build -f Dockerfile.demo -t datafuel-backend-demo .
docker run --rm -p 8000:8000 datafuel-backend-demo
# in another shell:
curl localhost:8000/api/v1/health
curl -X POST localhost:8000/api/v1/predictions/recommendation \
  -H 'Content-Type: application/json' \
  -d '{"lat":40.4168,"lon":-3.7038,"fuel_type":"gasolina_95","municipio":"Madrid","precio_actual":1.55}'
```

### B. Push to a PUBLIC registry (GHCR example — free)
```bash
echo "$GHCR_PAT" | docker login ghcr.io -u <YOUR-GH-USERNAME> --password-stdin
docker tag datafuel-backend-demo ghcr.io/<YOUR-GH-USERNAME>/datafuel-backend-demo:latest
docker push ghcr.io/<YOUR-GH-USERNAME>/datafuel-backend-demo:latest
# Then mark the GHCR package "Public" so Render needs no registry credentials.
```

### C. Deploy backend on Render
1. Edit [render.yaml](render.yaml): replace `<YOUR-GH-USERNAME>` in `image.url`.
2. Render → **New → Blueprint** (or **New → Web Service → Deploy an existing image**).
3. Set **`ALLOWED_ORIGINS`** to your exact Netlify origin (e.g. `https://datafuel.netlify.app`).
4. Wait for health check `/api/v1/health` to go green; spot-check `/api/v1/stations`.

### D. Deploy frontend on Netlify
1. New site from this repo (netlify.toml is auto-detected: base `frontend`, publish `dist`).
2. Set **`VITE_API_BASE_URL`** = your Render URL (e.g. `https://datafuel-backend.onrender.com`, no trailing slash) and **redeploy** (Vite inlines it at build time).
3. Verify a station search from the live site hits Render with no CORS / mixed-content error.

### E. Before the defense
- **Pre-warm** the Render service (free tier spins down after ~15 min idle → ~50 s cold start): load the site or `curl …/api/v1/health` a minute before presenting.
- Keep `docker compose up` (the existing [docker-compose.yml](docker-compose.yml)) ready on your laptop as a zero-dependency fallback.

### Alternative (skips the registry step) — Fly.io
`fly launch --dockerfile backend/Dockerfile.demo` then `fly deploy` uploads the
**local** build context, so it builds the baked image directly — no Git commit,
no registry. Verify Fly's current free allowance covers a ~1.3 GB image.

---

## Summary
- ✅ SQLite slice generated (210 MB, all stations, 30 days) — predictions, analytics, XAI, recommendation, stations all verified against it with the real app.
- ✅ Trained model (69 MB) included; SHAP enabled via the `xai` extra.
- ✅ Demo Docker image, `.dockerignore`, `render.yaml`, `netlify.toml`, `_redirects` prepared.
- ✅ No business/ML/API changes; production Dockerfile & compose untouched.
- ⏳ Outstanding (yours): build → push image → set `ALLOWED_ORIGINS` / `VITE_API_BASE_URL` → deploy → pre-warm.
