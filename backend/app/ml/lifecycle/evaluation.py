"""Acceptance gate: decide whether a freshly trained model may go live.

The candidate's metrics come from the trainer's time-based holdout (persisted
in the artifact). They are compared against the *currently active* model's
stored holdout metrics, plus optional absolute floors/ceilings. This is a
metrics-vs-metrics comparison, not a re-evaluation on a single shared holdout:
both models are scored on their own forward-in-time test slice — the honest
generalization signal this trainer already optimises for (see
``app.ml.training.entrenar``).

A candidate is **rejected** unless it is at least as good as the active model
within the configured tolerances. Rejection leaves the active model untouched.
Corrupted/empty artifacts and failed training runs are caught upstream (the
ArtifactStore validates file presence/size and the loader validates the bundle
shape); this module only judges *quality*.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

log = logging.getLogger(__name__)

Metrics = Mapping[str, float | None]


@dataclass(frozen=True, slots=True)
class AcceptanceThresholds:
    """Tolerances for accepting a candidate model.

    - ``max_mae`` / ``min_r2``: optional *absolute* guards applied to every
      candidate regardless of the active model.
    - ``max_mae_regression_pct``: the candidate's MAE may be at most this
      fraction worse than the active model's MAE (0.10 → 10 % worse allowed).
    - ``max_r2_absolute_drop``: the candidate's R² may fall at most this many
      absolute points below the active model's R².
    """

    max_mae: float | None = None
    min_r2: float | None = None
    max_mae_regression_pct: float = 0.10
    max_r2_absolute_drop: float = 0.05


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Outcome of the acceptance gate."""

    accepted: bool
    reason: str
    candidate: dict[str, float | None]
    baseline: dict[str, float | None] | None


def evaluate_candidate(
    candidate: Metrics,
    baseline: Metrics | None,
    thresholds: AcceptanceThresholds | None = None,
) -> EvaluationResult:
    """Return whether ``candidate`` may replace the active model."""
    th = thresholds or AcceptanceThresholds()
    cand: dict[str, float | None] = dict(candidate)
    base: dict[str, float | None] | None = dict(baseline) if baseline is not None else None

    mae = cand.get("mae")
    r2 = cand.get("r2")

    # 1. The candidate must report finite primary metrics.
    if mae is None or r2 is None:
        return _decide(
            False, cand, base, "candidate metrics incomplete (mae/r2 missing or non-finite)"
        )

    # 2. Absolute guards (applied even with no baseline).
    if th.max_mae is not None and mae > th.max_mae:
        return _decide(
            False, cand, base, f"MAE {mae:.5f} exceeds absolute ceiling {th.max_mae:.5f}"
        )
    if th.min_r2 is not None and r2 < th.min_r2:
        return _decide(False, cand, base, f"R2 {r2:.5f} below absolute floor {th.min_r2:.5f}")

    # 3. No active baseline → bootstrap-accept the first model.
    if base is None:
        return _decide(True, cand, base, "no active baseline; accepting first model")

    base_mae = base.get("mae")
    base_r2 = base.get("r2")
    if base_mae is None or base_r2 is None:
        return _decide(
            True, cand, base, "active baseline metrics unavailable; accepting on absolute guards"
        )

    # 4. Relative regression checks vs the active model.
    mae_ceiling = base_mae * (1.0 + th.max_mae_regression_pct)
    if mae > mae_ceiling:
        return _decide(
            False,
            cand,
            base,
            f"MAE {mae:.5f} worse than allowed {mae_ceiling:.5f} "
            f"(active {base_mae:.5f} +{th.max_mae_regression_pct:.0%})",
        )
    r2_floor = base_r2 - th.max_r2_absolute_drop
    if r2 < r2_floor:
        return _decide(
            False,
            cand,
            base,
            f"R2 {r2:.5f} below allowed {r2_floor:.5f} "
            f"(active {base_r2:.5f} -{th.max_r2_absolute_drop})",
        )

    return _decide(
        True,
        cand,
        base,
        f"candidate meets gate (mae {mae:.5f} vs active {base_mae:.5f}; "
        f"r2 {r2:.5f} vs active {base_r2:.5f})",
    )


def _decide(
    accepted: bool,
    candidate: dict[str, float | None],
    baseline: dict[str, float | None] | None,
    reason: str,
) -> EvaluationResult:
    if accepted:
        log.info("Model accepted: %s | candidate=%s baseline=%s", reason, candidate, baseline)
    else:
        log.warning("Model rejected: %s | candidate=%s baseline=%s", reason, candidate, baseline)
    return EvaluationResult(
        accepted=accepted, reason=reason, candidate=candidate, baseline=baseline
    )
