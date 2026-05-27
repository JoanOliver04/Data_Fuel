"""Unit tests for app.ml.xai.feature_importance_service."""

from __future__ import annotations

from typing import Any

import pytest

from app.ml.xai import feature_importance_service as fis


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    fis.reset_cache()


def test_normalized_to_percentages_summing_100(rf_artifact: dict[str, Any]) -> None:
    gi = fis.compute_global_importance(rf_artifact)
    assert gi.feature_count == 15
    total = sum(f.importance for f in gi.features)
    assert total == pytest.approx(100.0, abs=0.5)


def test_sorted_descending(rf_artifact: dict[str, Any]) -> None:
    gi = fis.compute_global_importance(rf_artifact)
    values = [f.importance for f in gi.features]
    assert values == sorted(values, reverse=True)


def test_enriched_with_display_copy(rf_artifact: dict[str, Any]) -> None:
    gi = fis.compute_global_importance(rf_artifact)
    top = gi.features[0]
    assert top.display_name
    assert top.description


def test_metadata_carried_through(rf_artifact: dict[str, Any]) -> None:
    gi = fis.compute_global_importance(rf_artifact)
    assert gi.r2 == pytest.approx(0.85)
    assert gi.mae == pytest.approx(0.04)
    assert gi.version == "test-rf-v1"
    assert gi.trained_at == "2026-01-01T00:00:00+00:00"


def test_result_is_cached(rf_artifact: dict[str, Any]) -> None:
    first = fis.compute_global_importance(rf_artifact)
    second = fis.compute_global_importance(rf_artifact)
    assert first is second  # served from the single-slot cache


def test_reset_cache_forces_recompute(rf_artifact: dict[str, Any]) -> None:
    first = fis.compute_global_importance(rf_artifact)
    fis.reset_cache()
    second = fis.compute_global_importance(rf_artifact)
    assert first is not second
    assert [f.feature for f in first.features] == [f.feature for f in second.features]


def test_falls_back_to_estimator_attribute(rf_artifact: dict[str, Any]) -> None:
    """With no persisted dict, importances come from model.feature_importances_."""
    artifact = dict(rf_artifact)
    artifact.pop("feature_importances")
    gi = fis.compute_global_importance(artifact)
    assert gi.feature_count == 15
    assert sum(f.importance for f in gi.features) == pytest.approx(100.0, abs=0.5)


def test_degenerate_all_zero_importances_splits_uniformly() -> None:
    artifact: dict[str, Any] = {
        "feature_importances": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0},
        "trained_at": "x",
    }
    gi = fis.compute_global_importance(artifact)
    assert sum(f.importance for f in gi.features) == pytest.approx(100.0, abs=0.5)
    assert all(f.importance == pytest.approx(25.0) for f in gi.features)


def test_raises_when_no_importances_available() -> None:
    artifact: dict[str, Any] = {"model": object(), "features_names": ["a", "b"]}
    with pytest.raises(ValueError, match="no usable feature importances"):
        fis.compute_global_importance(artifact)
