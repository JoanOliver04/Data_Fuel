"""Integration tests for POST /api/v1/predictions/recommendation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

_VALID_PAYLOAD = {
    "lat": 39.4697,
    "lon": -0.3774,
    "fuel_type": "gasolina_95",
    "municipio": "Valencia",
    "comarca": "Horta de València",
    "precio_actual": 1.529,
}


def _make_artifact(predict_price: float, r2: float = 0.95) -> dict[str, Any]:
    """Build a minimal fake artifact that recommendation_service can consume."""
    le = MagicMock()
    le.classes_ = np.array(["Alzira", "Horta de València", "Ribera Alta", "Valencia"])
    le.transform.return_value = np.array([0])

    model = MagicMock()
    model.predict.return_value = np.array([predict_price])

    return {
        "model": model,
        "label_encoder_municipio": le,
        "label_encoder_comarca": le,
        "features_names": [
            "distancia", "tipo_combustible", "dia_de_la_semana",
            "mes", "año", "municipio_enc", "comarca_enc",
        ],
        "trained_at": "2026-01-01T00:00:00+00:00",
        "mae": 0.01,
        "r2": r2,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_reposta_ahora_when_price_rises(api_client) -> None:
    # precio_predicho (2.0) > precio_actual (1.529) -> REPOSTA AHORA
    artifact = _make_artifact(predict_price=2.0)
    with patch("app.ml.inference.model_loader._modelo", artifact):
        resp = await api_client.post(
            "/api/v1/predictions/recommendation", json=_VALID_PAYLOAD
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["veredicto"] == "REPOSTA AHORA"
    assert data["precio_predicho"] == pytest.approx(2.0, abs=0.001)
    assert data["variacion_pct"] > 0


async def test_espera_when_price_falls(api_client) -> None:
    # precio_predicho (1.2) < precio_actual (1.529) -> ESPERA
    artifact = _make_artifact(predict_price=1.2)
    with patch("app.ml.inference.model_loader._modelo", artifact):
        resp = await api_client.post(
            "/api/v1/predictions/recommendation", json=_VALID_PAYLOAD
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["veredicto"] == "ESPERA"
    assert data["variacion_pct"] < 0


async def test_response_has_all_fields(api_client) -> None:
    artifact = _make_artifact(predict_price=1.6, r2=0.78)
    with patch("app.ml.inference.model_loader._modelo", artifact):
        resp = await api_client.post(
            "/api/v1/predictions/recommendation", json=_VALID_PAYLOAD
        )
    assert resp.status_code == 200
    data = resp.json()
    for field in ("veredicto", "precio_actual", "precio_predicho", "variacion_pct", "advice", "confianza"):
        assert field in data, f"missing field: {field}"
    assert data["confianza"] == pytest.approx(0.78, abs=0.001)


async def test_503_when_model_not_loaded(api_client) -> None:
    with patch("app.ml.inference.model_loader._modelo", None):
        resp = await api_client.post(
            "/api/v1/predictions/recommendation", json=_VALID_PAYLOAD
        )
    assert resp.status_code == 503


async def test_422_invalid_lat(api_client) -> None:
    bad = {**_VALID_PAYLOAD, "lat": 200.0}
    resp = await api_client.post("/api/v1/predictions/recommendation", json=bad)
    assert resp.status_code == 422


async def test_422_invalid_fuel_type(api_client) -> None:
    bad = {**_VALID_PAYLOAD, "fuel_type": "diesel_magico"}
    resp = await api_client.post("/api/v1/predictions/recommendation", json=bad)
    assert resp.status_code == 422
