"""Unit tests for app.ml.lifecycle.evaluation — the acceptance gate."""

from __future__ import annotations

from app.ml.lifecycle.evaluation import (
    AcceptanceThresholds,
    EvaluationResult,
    evaluate_candidate,
)


def _m(mae: float | None, r2: float | None, rmse: float = 0.02) -> dict[str, float | None]:
    return {"mae": mae, "rmse": rmse, "r2": r2, "r2_oob": r2}


# ── bootstrap (no baseline) ────────────────────────────────────────────────────


def test_accept_first_model_when_no_baseline() -> None:
    result = evaluate_candidate(_m(0.05, 0.8), baseline=None)
    assert result.accepted is True
    assert "first model" in result.reason
    assert result.baseline is None


def test_first_model_still_subject_to_absolute_guards() -> None:
    th = AcceptanceThresholds(max_mae=0.03)
    result = evaluate_candidate(_m(0.05, 0.8), baseline=None, thresholds=th)
    assert result.accepted is False
    assert "absolute ceiling" in result.reason


# ── relative comparison ────────────────────────────────────────────────────────


def test_accept_when_better_than_baseline() -> None:
    result = evaluate_candidate(_m(0.04, 0.92), baseline=_m(0.05, 0.90))
    assert result.accepted is True


def test_accept_when_slightly_worse_within_tolerance() -> None:
    # +8% MAE, within default 10% allowance; R2 drop 0.02 within 0.05.
    result = evaluate_candidate(_m(0.054, 0.88), baseline=_m(0.05, 0.90))
    assert result.accepted is True


def test_reject_when_mae_regresses_beyond_pct() -> None:
    # +20% MAE > default 10% allowance.
    result = evaluate_candidate(_m(0.06, 0.90), baseline=_m(0.05, 0.90))
    assert result.accepted is False
    assert "MAE" in result.reason


def test_reject_when_r2_drops_beyond_allowance() -> None:
    # R2 drops 0.10 > default 0.05 allowance.
    result = evaluate_candidate(_m(0.05, 0.80), baseline=_m(0.05, 0.90))
    assert result.accepted is False
    assert "R2" in result.reason


def test_custom_tolerances_respected() -> None:
    th = AcceptanceThresholds(max_mae_regression_pct=0.30, max_r2_absolute_drop=0.15)
    # +20% MAE and 0.10 R2 drop — rejected by defaults, accepted by loose th.
    assert evaluate_candidate(_m(0.06, 0.80), baseline=_m(0.05, 0.90)).accepted is False
    assert evaluate_candidate(_m(0.06, 0.80), baseline=_m(0.05, 0.90), thresholds=th).accepted


# ── invalid / missing metrics ──────────────────────────────────────────────────


def test_reject_when_candidate_mae_missing() -> None:
    result = evaluate_candidate(_m(None, 0.90), baseline=_m(0.05, 0.90))
    assert result.accepted is False
    assert "incomplete" in result.reason


def test_reject_when_candidate_r2_missing() -> None:
    result = evaluate_candidate(_m(0.05, None), baseline=_m(0.05, 0.90))
    assert result.accepted is False


def test_accept_on_absolute_guards_when_baseline_metrics_unusable() -> None:
    result = evaluate_candidate(_m(0.05, 0.90), baseline=_m(None, None))
    assert result.accepted is True
    assert "baseline metrics unavailable" in result.reason


# ── absolute guards ─────────────────────────────────────────────────────────────


def test_absolute_mae_ceiling_rejects() -> None:
    th = AcceptanceThresholds(max_mae=0.04)
    result = evaluate_candidate(_m(0.05, 0.95), baseline=_m(0.06, 0.90), thresholds=th)
    assert result.accepted is False
    assert "ceiling" in result.reason


def test_absolute_r2_floor_rejects() -> None:
    th = AcceptanceThresholds(min_r2=0.85)
    result = evaluate_candidate(_m(0.03, 0.80), baseline=_m(0.05, 0.78), thresholds=th)
    assert result.accepted is False
    assert "floor" in result.reason


# ── result shape ─────────────────────────────────────────────────────────────


def test_result_carries_metrics() -> None:
    result = evaluate_candidate(_m(0.04, 0.92), baseline=_m(0.05, 0.90))
    assert isinstance(result, EvaluationResult)
    assert result.candidate["mae"] == 0.04
    assert result.baseline is not None and result.baseline["r2"] == 0.90
