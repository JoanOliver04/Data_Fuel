"""Unit tests for app.ml.xai.shap_explainer."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from app.ml.xai import shap_explainer


@pytest.fixture(autouse=True)
def _clean() -> None:
    shap_explainer.reset()


def _vector(rf_artifact: dict[str, Any]) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.normal(size=(1, len(rf_artifact["features_names"]))).astype(float)


def test_is_available() -> None:
    assert shap_explainer.is_available() is True


def test_explain_is_additive(rf_artifact: dict[str, Any]) -> None:
    model = rf_artifact["model"]
    names = rf_artifact["features_names"]
    vec = _vector(rf_artifact)

    expl = shap_explainer.explain(model, vec, names)
    assert expl is not None
    # Local accuracy: base_value + Σ contributions == model prediction.
    direct = float(model.predict(vec)[0])
    summed = expl.base_value + sum(c.impact for c in expl.contributions)
    assert summed == pytest.approx(direct, abs=1e-3)
    assert expl.prediction == pytest.approx(direct, abs=1e-3)


def test_contributions_cover_all_features_sorted(rf_artifact: dict[str, Any]) -> None:
    expl = shap_explainer.explain(
        rf_artifact["model"], _vector(rf_artifact), rf_artifact["features_names"]
    )
    assert expl is not None
    assert len(expl.contributions) == 15
    magnitudes = [abs(c.impact) for c in expl.contributions]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_warm_builds_singleton(rf_artifact: dict[str, Any]) -> None:
    assert shap_explainer.warm(rf_artifact["model"]) is True
    assert shap_explainer._explainer is not None
    built_for = shap_explainer._explainer_model_id
    # Re-explaining with the same model reuses the same explainer object.
    shap_explainer.explain(rf_artifact["model"], _vector(rf_artifact), rf_artifact["features_names"])
    assert shap_explainer._explainer_model_id == built_for


def test_hot_reload_rebuilds_for_new_model(rf_artifact: dict[str, Any]) -> None:
    from sklearn.ensemble import RandomForestRegressor

    shap_explainer.warm(rf_artifact["model"])
    first_id = shap_explainer._explainer_model_id

    other = RandomForestRegressor(n_estimators=5, max_depth=3, random_state=1)
    rng = np.random.default_rng(1)
    other.fit(rng.normal(size=(50, 15)), rng.normal(size=50))
    shap_explainer.explain(other, _vector(rf_artifact), rf_artifact["features_names"])
    assert shap_explainer._explainer_model_id != first_id


def test_returns_none_when_shap_missing(
    rf_artifact: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shap_explainer, "shap", None)
    assert shap_explainer.is_available() is False
    assert shap_explainer.warm(rf_artifact["model"]) is False
    assert (
        shap_explainer.explain(
            rf_artifact["model"], _vector(rf_artifact), rf_artifact["features_names"]
        )
        is None
    )


def test_returns_none_when_build_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_model: Any) -> Any:
        raise RuntimeError("unsupported model")

    monkeypatch.setattr(shap_explainer.shap, "TreeExplainer", _boom)
    out = shap_explainer.explain(object(), np.zeros((1, 15)), ["f"] * 15)
    assert out is None


def test_returns_none_when_shap_values_fail(
    rf_artifact: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Bad:
        expected_value = np.array([1.5])

        def shap_values(self, _x: Any) -> Any:
            raise ValueError("kaboom")

    monkeypatch.setattr(shap_explainer.shap, "TreeExplainer", lambda _m: _Bad())
    out = shap_explainer.explain(
        rf_artifact["model"], _vector(rf_artifact), rf_artifact["features_names"]
    )
    assert out is None
