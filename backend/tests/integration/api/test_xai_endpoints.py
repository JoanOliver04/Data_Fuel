"""Integration tests for the XAI endpoints.

* GET  /api/v1/xai/global-feature-importance
* POST /api/v1/xai/explain-recommendation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

_PAYLOAD = {
    "lat": 39.4697,
    "lon": -0.3774,
    "fuel_type": "gasolina_95",
    "municipio": "Valencia",
    "station_lat": 39.45,
    "station_lon": -0.39,
    "precio_actual": 1.529,
}


# ── GET /global-feature-importance ──────────────────────────────────────────


async def test_global_importance_ok(api_client, rf_artifact: dict[str, Any]) -> None:
    with patch("app.ml.inference.model_loader._modelo", rf_artifact):
        resp = await api_client.get("/api/v1/xai/global-feature-importance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_count"] == 15
    assert data["model_r2"] == pytest.approx(0.85)
    assert data["model_version"] == "test-rf-v1"
    importances = [f["importance"] for f in data["features"]]
    assert importances == sorted(importances, reverse=True)
    assert sum(importances) == pytest.approx(100.0, abs=0.5)
    assert data["features"][0]["display_name"]


async def test_global_importance_503_when_no_model(api_client) -> None:
    with patch("app.ml.inference.model_loader._modelo", None):
        resp = await api_client.get("/api/v1/xai/global-feature-importance")
    assert resp.status_code == 503


async def test_global_importance_503_when_no_importances(api_client) -> None:
    bad: dict[str, Any] = {"model": object(), "features_names": ["a", "b"]}
    with patch("app.ml.inference.model_loader._modelo", bad):
        resp = await api_client.get("/api/v1/xai/global-feature-importance")
    assert resp.status_code == 503


# ── POST /explain-recommendation ────────────────────────────────────────────


async def test_explain_ok_with_shap(api_client, rf_artifact: dict[str, Any]) -> None:
    with patch("app.ml.inference.model_loader._modelo", rf_artifact):
        resp = await api_client.post("/api/v1/xai/explain-recommendation", json=_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["shap_available"] is True
    assert data["veredicto"] in ("REPOSTA AHORA", "ESPERA")
    assert data["reasoning"]
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["feature_importance_local"]) == 15
    assert len(data["feature_importance_global"]) <= 10
    assert len(data["top_positive_factors"]) <= 5
    assert len(data["top_negative_factors"]) <= 5
    # Every local factor carries a signed impact and a direction.
    for f in data["feature_importance_local"]:
        assert f["direction"] in ("lowers", "raises")
    # top_positive == price-lowering, top_negative == price-raising.
    assert all(f["impact"] < 0 for f in data["top_positive_factors"])
    assert all(f["impact"] > 0 for f in data["top_negative_factors"])


async def test_explain_additivity(api_client, rf_artifact: dict[str, Any]) -> None:
    with patch("app.ml.inference.model_loader._modelo", rf_artifact):
        resp = await api_client.post("/api/v1/xai/explain-recommendation", json=_PAYLOAD)
    data = resp.json()
    total = data["base_value"] + sum(f["impact"] for f in data["feature_importance_local"])
    assert total == pytest.approx(data["prediction"], abs=5e-3)


async def test_explain_503_when_no_model(api_client) -> None:
    with patch("app.ml.inference.model_loader._modelo", None):
        resp = await api_client.post("/api/v1/xai/explain-recommendation", json=_PAYLOAD)
    assert resp.status_code == 503


async def test_explain_degrades_without_shap(
    api_client, rf_artifact: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.ml.xai.shap_explainer.shap", None)
    with patch("app.ml.inference.model_loader._modelo", rf_artifact):
        resp = await api_client.post("/api/v1/xai/explain-recommendation", json=_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["shap_available"] is False
    assert data["feature_importance_local"] == []
    assert data["top_positive_factors"] == []
    # Reasoning still present (fallback) and global importance still served.
    assert data["reasoning"]
    assert len(data["feature_importance_global"]) <= 10
    assert "no está disponible" in data["reasoning"]


async def test_explain_422_invalid_payload(api_client) -> None:
    bad = {**_PAYLOAD, "lat": 999.0}
    resp = await api_client.post("/api/v1/xai/explain-recommendation", json=bad)
    assert resp.status_code == 422
