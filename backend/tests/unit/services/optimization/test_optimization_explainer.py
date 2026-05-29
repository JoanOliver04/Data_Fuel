"""Unit tests for the deterministic optimization explainer."""

from __future__ import annotations

import pytest

from app.services.optimization import optimization_explainer as ex
from app.services.optimization.optimization_profiles import OptimizationProfile


@pytest.mark.parametrize("profile", list(OptimizationProfile))
def test_every_profile_has_es_and_en_rationale(profile: OptimizationProfile) -> None:
    es = ex.explain(profile=profile, locale="es")
    en = ex.explain(profile=profile, locale="en")
    assert es and en
    assert es != en  # genuinely localised, not a passthrough


def test_default_locale_is_spanish() -> None:
    assert ex.explain(profile=OptimizationProfile.BALANCED) == ex.explain(
        profile=OptimizationProfile.BALANCED, locale="es"
    )


def test_unknown_locale_falls_back_to_default() -> None:
    assert ex.explain(profile=OptimizationProfile.FASTEST, locale="de") == ex.explain(
        profile=OptimizationProfile.FASTEST, locale="es"
    )


def test_addenda_appended_when_data_present() -> None:
    text = ex.explain(
        profile=OptimizationProfile.COMMUTER,
        eta_minutes=12.0,
        traffic_delay_minutes=3.0,
        savings_vs_runner_up=1.5,
        locale="en",
    )
    assert "12 min" in text
    assert "3 min" in text
    assert "1.50" in text


def test_addenda_omitted_when_data_absent_or_zero() -> None:
    base = ex.explain(profile=OptimizationProfile.CHEAPEST, locale="en")
    with_zeros = ex.explain(
        profile=OptimizationProfile.CHEAPEST,
        eta_minutes=0.0,
        traffic_delay_minutes=0.0,
        savings_vs_runner_up=0.0,
        locale="en",
    )
    assert base == with_zeros  # nothing appended for zero/None figures


def test_fastest_mentions_congestion() -> None:
    text = ex.explain(profile=OptimizationProfile.FASTEST, locale="en").lower()
    assert "congest" in text or "traffic" in text
