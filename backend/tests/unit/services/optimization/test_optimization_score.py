"""Unit tests for the multi-objective scoring engine."""

from __future__ import annotations

import pytest

from app.services.optimization.optimization_profiles import (
    PROFILE_WEIGHTS,
    OptimizationProfile,
)
from app.services.optimization.optimization_score import (
    CostComponents,
    evaluate,
    optimization_score,
    time_cost,
    traffic_penalty,
)


# ── time_cost ──────────────────────────────────────────────────────────────


def test_time_cost_default_rate() -> None:
    # 20 min at 15 €/h → 5 €.
    assert time_cost(20.0, 15.0) == pytest.approx(5.0)


def test_time_cost_none_eta_is_zero() -> None:
    assert time_cost(None, 15.0) == 0.0


def test_time_cost_nonpositive_eta_is_zero() -> None:
    assert time_cost(0.0, 15.0) == 0.0


# ── traffic_penalty ──────────────────────────────────────────────────────────


def test_traffic_penalty_example() -> None:
    # 15 min delay (900 s) at 0.25 €/min → 3.75 €.
    assert traffic_penalty(900, 0.25) == pytest.approx(3.75)


def test_traffic_penalty_none_is_zero() -> None:
    assert traffic_penalty(None, 0.25) == 0.0


def test_traffic_penalty_zero_delay_is_zero() -> None:
    assert traffic_penalty(0, 0.25) == 0.0


# ── optimization_score ───────────────────────────────────────────────────────


def test_score_is_weighted_sum() -> None:
    comp = CostComponents(
        fuel_cost=72.5, travel_cost=1.2, time_cost=0.95, traffic_penalty=0.0, eta_minutes=4.0
    )
    weights = PROFILE_WEIGHTS[OptimizationProfile.BALANCED]
    expected = 0.40 * 72.5 + 0.25 * 1.2 + 0.25 * 0.95 + 0.10 * 0.0
    assert optimization_score(comp, weights) == pytest.approx(expected)


def test_equal_components_score_independent_of_profile() -> None:
    # When all four components are equal, every (sum-to-1) profile yields that value.
    comp = CostComponents(
        fuel_cost=5.0, travel_cost=5.0, time_cost=5.0, traffic_penalty=5.0, eta_minutes=10.0
    )
    scores = {
        p: optimization_score(comp, PROFILE_WEIGHTS[p]) for p in OptimizationProfile
    }
    assert all(s == pytest.approx(5.0) for s in scores.values())


# ── evaluate ─────────────────────────────────────────────────────────────────


def test_evaluate_assembles_components_and_score() -> None:
    res = evaluate(
        fuel_cost=72.5,
        travel_cost=1.2,
        eta_minutes=4.0,
        traffic_delay_seconds=0,
        profile=OptimizationProfile.BALANCED,
        time_cost_per_hour=15.0,
        traffic_penalty_factor=0.25,
    )
    assert res.profile is OptimizationProfile.BALANCED
    assert res.components.time_cost == pytest.approx(1.0)  # 4 min @ 15 €/h
    assert res.components.traffic_penalty == 0.0
    assert res.components.eta_minutes == 4.0
    expected = 0.40 * 72.5 + 0.25 * 1.2 + 0.25 * 1.0 + 0.10 * 0.0
    assert res.score == pytest.approx(expected, abs=1e-3)


def test_evaluate_degrades_without_routing_data() -> None:
    # No ETA / traffic → time + traffic terms vanish, score = weighted fuel+travel.
    res = evaluate(
        fuel_cost=60.0,
        travel_cost=2.0,
        eta_minutes=None,
        traffic_delay_seconds=None,
        profile=OptimizationProfile.FASTEST,
        time_cost_per_hour=15.0,
        traffic_penalty_factor=0.25,
    )
    assert res.components.time_cost == 0.0
    assert res.components.traffic_penalty == 0.0
    expected = 0.15 * 60.0 + 0.15 * 2.0
    assert res.score == pytest.approx(expected, abs=1e-3)
