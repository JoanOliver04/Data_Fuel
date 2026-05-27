# 0009 — Explainable AI (XAI) layer

- **Status:** Accepted
- **Date:** 2026-05-27
- **Deciders:** Data Fuel maintainers

## Context

The Random Forest *recommendation* model (`POST /api/v1/predictions/recommendation`,
see [ADR 0008](0008-automated-ml-retraining.md)) returns a binary verdict —
**REPOSTA AHORA** / **ESPERA** — plus a forecast and a confidence number. Users
(and reviewers, and the author defending the project) reasonably ask *why*. A
verdict with no rationale is hard to trust and impossible to audit: is the model
keying on real market signal, or on a spurious artifact?

We want a production-safe explainability layer that:

- exposes **global** feature importance (what the model relies on overall);
- produces **local**, per-prediction attributions (why *this* recommendation);
- renders both as a **human-readable** rationale a non-technical user can follow;
- never retrains during a request, never needs a GPU, and never destabilises the
  recommendation pipeline;
- stays inside the existing Clean Architecture, passes `mypy --strict`, and keeps
  the new code at ≥90 % coverage.

Crucially, the model, its 15-column feature schema, and the endpoint contract are
**fixed** — the XAI layer observes them, it does not change them.

## Decision

Add a read-only `app/ml/xai/` package and two endpoints under `/api/v1/xai`.

```
feature_metadata  ─ locale-keyed labels/descriptions/reasoning fragments (es, en)
feature_importance_service ─ normalized, sorted, cached global importances
shap_explainer    ─ process-singleton shap.TreeExplainer, guarded + graceful
reasoning_engine  ─ deterministic, template-based NL generation
```

Key choices:

- **SHAP for local attribution.** SHAP (SHapley Additive exPlanations) gives each
  feature a contribution such that `base_value + Σ contributions == prediction`
  exactly (local accuracy). This additivity is what makes the UI honest: the
  green/red impacts literally sum to the forecast, not a hand-wavy "importance".
  Shapley values are the unique attribution satisfying local accuracy,
  consistency, and missingness — a principled, defensible basis.

- **`TreeExplainer` specifically.** Our model is a `RandomForestRegressor`.
  TreeSHAP computes exact Shapley values for tree ensembles in low-order
  polynomial time by exploiting tree structure — no sampling, no background
  dataset, fully deterministic. On the production artifact (150 trees, depth 14)
  it builds in **~40 ms** and explains one prediction in **~100 ms** on CPU,
  comfortably inside the <300 ms budget. `KernelExplainer` (model-agnostic) would
  cost orders of magnitude more and be stochastic.

- **Original, human-readable feature names.** The model consumes a 15-column
  vector with label-encoded `municipio_enc` / `comarca_enc`. SHAP values are
  computed on that exact vector but mapped back to curated names + descriptions
  via `feature_metadata` — the API never leaks encoded indices or raw column
  positions.

- **Singleton explainer, identity-keyed.** The explainer is built once and cached
  by `id(model)`. A hot model swap (ADR 0008) rebinds to a new object, which is
  detected and triggers a one-time rebuild — never a per-request build. Reads are
  lock-free; only construction is serialised. It is also warmed in the FastAPI
  lifespan so the first request pays no build cost.

- **One feature vector, single-sourced.** `recommendation_service.construir_features`
  now builds the inference vector and `derivar_veredicto` maps prediction→verdict;
  both the recommendation endpoint and the explain endpoint call them. The verdict
  and the explained vector therefore *cannot* diverge between the two surfaces,
  and there is no duplicate DB work.

- **Deterministic reasoning, not an LLM.** The natural-language rationale is
  assembled from curated, locale-keyed fragments keyed on the SHAP sign of each
  top factor. It is reproducible, auditable, free, offline, and — critically —
  **cannot hallucinate**. (The project *has* an optional LLM layer at
  `/api/v1/ai/*`; XAI deliberately does not depend on it.)

- **Graceful degradation everywhere.** `shap` is an **optional** dependency (new
  `[xai]` extra). If it is absent or the explainer fails, `explain` returns
  `None`; the endpoint still answers `200` with global importance + a fallback
  rationale and `shap_available: false`. A missing model yields `503`. The
  recommendation pipeline is never affected.

- **Threading + rate limits.** The CPU-bound predict + SHAP runs in
  `asyncio.to_thread` so the event loop stays responsive; both endpoints are
  slowapi-rate-limited (`XAI_RATE_LIMIT`, default 20/min).

## Consequences

**Positive**
- Every recommendation is now defensible: a global importance chart, an exact
  additive local breakdown, and a plain-language "why".
- Mathematically correct (local accuracy holds to 1e-3 in tests) yet readable by
  non-technical users.
- Zero blast radius: optional dependency, graceful degradation, model/schema/
  contract untouched, existing tests green.

**Negative / costs**
- `shap` pulls `numba` + `llvmlite` (~40 MB) when the extra is installed. Kept
  optional so a base install stays lean.
- SHAP adds ~100 ms to the explain call (not to the recommendation call). It is a
  separate, rate-limited, opt-in endpoint, so this never touches the hot path.
- `is_low_cost` / `es_autopista` are held at neutral defaults at inference time
  (see README §6.1), so their local SHAP impact is ~0 here — a property of the
  serving contract, not of the explainer.

**Neutral**
- Global importance is impurity-based (the trainer's persisted
  `feature_importances_`), which can inflate high-cardinality features; the
  *local* story is SHAP-based and is the one shown per recommendation.

## Alternatives considered

- **`KernelExplainer` / model-agnostic SHAP** — works for any model but is
  sampling-based, stochastic, needs a background set, and is ~100–1000× slower.
  Rejected: we have a tree model, so exact TreeSHAP is strictly better.
- **LIME** — local surrogate models; approximate, non-additive, and sensitive to
  perturbation settings. Rejected in favour of exact, additive Shapley values.
- **Bare `feature_importances_` only** — trivial and free, but global-only and
  impurity-biased; gives no per-recommendation answer. Kept as the *global* view
  and the SHAP-unavailable fallback, not as the whole story.
- **LLM-generated explanations** — fluent, but non-deterministic and can
  hallucinate causes the model never used — unacceptable for an explainability
  feature whose whole point is trust. Rejected for deterministic templates; the
  optional LLM layer remains available for *conversational* enrichment elsewhere.
- **Precompute/store SHAP at training time** — pointless here: inputs are
  per-request (live municipio/comarca aggregates), so attribution must be
  computed at explain time anyway.
