"""Unit tests for optimization profiles and their weights."""

from __future__ import annotations

import pytest

from app.services.optimization.optimization_profiles import (
    DEFAULT_PROFILE,
    PROFILE_WEIGHTS,
    OptimizationProfile,
    ProfileWeights,
    weights_for,
)


def test_all_profiles_have_weights() -> None:
    assert set(PROFILE_WEIGHTS) == set(OptimizationProfile)


@pytest.mark.parametrize("profile", list(OptimizationProfile))
def test_weights_sum_to_one(profile: OptimizationProfile) -> None:
    w = PROFILE_WEIGHTS[profile]
    assert w.fuel + w.distance + w.time + w.traffic == pytest.approx(1.0)


def test_default_profile_is_balanced() -> None:
    assert DEFAULT_PROFILE is OptimizationProfile.BALANCED


def test_cheapest_weights_fuel_heaviest() -> None:
    w = PROFILE_WEIGHTS[OptimizationProfile.CHEAPEST]
    assert w.fuel == max(w.fuel, w.distance, w.time, w.traffic)


def test_fastest_weights_time_heaviest() -> None:
    w = PROFILE_WEIGHTS[OptimizationProfile.FASTEST]
    assert w.time == max(w.fuel, w.distance, w.time, w.traffic)


def test_invalid_weights_rejected() -> None:
    with pytest.raises(ValueError, match=r"sum to 1\.0"):
        ProfileWeights(fuel=0.5, distance=0.5, time=0.5, traffic=0.5)


def test_negative_weights_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ProfileWeights(fuel=1.2, distance=-0.2, time=0.0, traffic=0.0)


def test_weights_for_returns_profile_weights() -> None:
    assert weights_for(OptimizationProfile.BALANCED) is PROFILE_WEIGHTS[OptimizationProfile.BALANCED]


def test_weights_for_override_wins() -> None:
    override = ProfileWeights(fuel=1.0, distance=0.0, time=0.0, traffic=0.0)
    assert weights_for(OptimizationProfile.FASTEST, override) is override
