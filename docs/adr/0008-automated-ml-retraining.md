# 0008 — Automated ML retraining lifecycle

- **Status:** Accepted
- **Date:** 2026-05-24
- **Deciders:** Data Fuel maintainers

## Context

The Random Forest *recommendation* model (`POST /api/v1/predictions/recommendation`)
was trained once, by hand, and committed as `artifacts/modelo_combustible.pkl`.
As MITECO history grows the model goes stale, and there was no safe, repeatable
way to retrain, evaluate, and promote a new one without editing files by hand
and restarting the service.

(Note: the on-demand Ridge model behind `GET /predictions/{station}/{fuel}` is a
*separate* thing — it retrains itself in memory per request and owns no
artifact. It is intentionally out of scope here and untouched.)

We want: a weekly automated retrain, manual CLI control, versioned artifacts,
metric-gated promotion that never ships a worse model, hot reload without
downtime, and an audit trail — all within the existing Clean Architecture,
async correctness, `mypy --strict`, and high coverage.

## Decision

Add `app/ml/lifecycle/` with a `RetrainPipeline` orchestrating:

```
export dataset → train (worker thread) → version + sidecars
→ evaluate vs active → activate (atomic) → hot-reload → invalidate caches
→ record history
```

Key choices:

- **Versioned artifacts, atomic & symlink-free activation.** `ArtifactStore`
  keeps `artifacts/active/` and `artifacts/archived/<UTC-version>/` with
  `metadata.json` + `metrics.json` sidecars. Activation swaps each file into
  `active/` with `os.replace` — atomic on POSIX and on same-volume NTFS — so we
  avoid Windows symlink privileges and never expose a partial model. The model
  loader resolves `active/model.pkl` first and falls back to the legacy
  single-file artifact, preserving backward compatibility.

- **Acceptance gate.** `evaluate_candidate` compares the candidate's holdout
  metrics (MAE/RMSE/R²) against the active model's stored metrics plus optional
  absolute guards. A candidate is rejected unless within
  `RETRAIN_MAX_MAE_REGRESSION_PCT` and `RETRAIN_MAX_R2_ABSOLUTE_DROP`; the first
  model bootstrap-accepts. A rejected or invalid model is never activated.

- **Hot reload with rollback.** `reload_modelo()` rebinds the in-memory model
  atomically under a lock; `get_modelo()` stays lock-free so in-flight requests
  keep their bundle (model + encoders travel together — never mismatched). If a
  reload fails after activation, the pipeline re-activates the previous version
  and the run is recorded as FAILED.

- **Training in a thread.** Only the CPU-bound fit is offloaded via
  `asyncio.to_thread`; scikit-learn releases the GIL in native code, so the
  event loop and request serving stay responsive.

- **History.** Every attempt (activated/rejected/failed) is appended to a
  `training_runs` table via `TrainingRunRepository` — timings, dataset size,
  metrics, version, and reason — for a future dashboard. History writes are
  best-effort and never change the pipeline outcome.

- **Scheduling.** A weekly APScheduler `CronTrigger` (`RETRAIN_CRON`, UTC,
  default Sunday 03:00), opt-in via `RETRAIN_ENABLED`, with `max_instances=1`,
  `coalesce=True`, and a wall-clock `RETRAIN_TIMEOUT_SECONDS`.

- **CLI.** `python -m app.ml.training.{retrain,evaluate,activate}` with distinct
  exit codes (0 activated, 2 rejected, 1 failed/error) for cron/CI use.

The dataset export moved from `scripts/` into
`app.services.dataset_export_service` (importable production code); the script
is now a thin re-exporting wrapper.

## Consequences

**Positive**
- Hands-off weekly retrain plus manual control; promotion is metric-gated so a
  degraded model can never replace a working one.
- No-downtime hot reload; the active model is always a known-good artifact.
- Full provenance: versioned artifacts + a queryable run history.
- Fully testable without a DB, MITECO, or a real fit (all collaborators inject).

**Negative / costs**
- The retrain runs in the API process; at scale this belongs in a dedicated
  worker. CPU contention during a fit is mitigated by the GIL release but not
  eliminated.
- `asyncio.wait_for` cannot kill the worker thread on timeout — an over-running
  fit is abandoned by the awaiter and finishes orphaned in the background.
- Acceptance compares each model on its *own* forward-in-time holdout, not a
  single shared test set; this matches the trainer's honest-generalization
  design but is not a like-for-like re-scoring.

**Neutral**
- Activation is file-swap based; a running server picks up a manual `activate`
  only on restart (or the in-process scheduler's next reload).

## Alternatives considered

- **Directory symlink for `active/`** — matches a common MLOps layout but needs
  Developer Mode/admin on Windows and can fail silently. Rejected for atomic
  `os.replace`.
- **Separate worker/queue (Celery, RQ)** — the right answer at scale, but heavy
  for a single-process portfolio app. The injectable pipeline can be moved
  behind a worker later with no orchestration changes.
- **MLflow / model registry** — powerful but a large dependency; the
  filesystem `ArtifactStore` + `training_runs` table covers current needs.
- **Always promote the newly trained model** — simplest, but risks shipping a
  regression; rejected in favour of the acceptance gate.
