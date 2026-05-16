"""AI refuel-advice service using the trained Random Forest model.

Replicates EXACTLY the feature preprocessing from entrenar.py so that the
feature vector passed to model.predict() is identical to what the model saw
during training. Any divergence here produces garbage predictions.

Feature order (must match FEATURE_COLUMNS in entrenar.py):
    distancia, tipo_combustible, dia_de_la_semana, mes, año,
    municipio_enc, comarca_enc
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np

from app.domain.entities.fuel_type import FuelType
from app.ml.data.fuel_type_mapping import FUEL_TYPE_TO_ID
from app.ml.inference.model_loader import get_modelo
from app.services.geopy_distance_service import calcular_distancia_geodesica

log = logging.getLogger(__name__)

_ALZIRA: tuple[float, float] = (39.1496, -0.4373)


def _encode(le: Any, value: str) -> int:
    """Encode a categorical label; falls back to 0 for unseen values."""
    if value in le.classes_:
        return int(le.transform([value])[0])
    log.warning("Label '%s' not in encoder classes — using class 0 as fallback", value)
    return 0


def generar_recomendacion(
    lat: float,
    lon: float,
    fuel_type: FuelType,
    municipio: str,
    comarca: str,
    precio_actual: float,
) -> dict[str, Any]:
    """Predict next-week price and return a refuel-now-or-wait verdict.

    Raises RuntimeError if the model is not loaded (caller must convert to 503).
    """
    artifact = get_modelo()
    if artifact is None:
        raise RuntimeError("ML model is not loaded")

    model = artifact["model"]
    le_municipio = artifact["label_encoder_municipio"]
    le_comarca = artifact["label_encoder_comarca"]

    today = date.today()
    distancia = calcular_distancia_geodesica(_ALZIRA, (lat, lon))
    tipo_combustible = FUEL_TYPE_TO_ID[fuel_type]
    municipio_enc = _encode(le_municipio, municipio)
    comarca_enc = _encode(le_comarca, comarca)

    features = np.array(
        [[
            distancia,
            tipo_combustible,
            today.weekday(),
            today.month,
            today.year,
            municipio_enc,
            comarca_enc,
        ]],
        dtype=float,
    )

    precio_predicho = float(model.predict(features)[0])
    variacion_pct = round((precio_predicho - precio_actual) / precio_actual * 100, 2)

    if precio_predicho > precio_actual:
        veredicto = "REPOSTA AHORA"
        advice = (
            f"Reposta ahora, el precio subirá un {abs(variacion_pct):.1f}%"
            " la próxima semana"
        )
    else:
        veredicto = "ESPERA"
        advice = (
            f"Espera, el precio bajará un {abs(variacion_pct):.1f}%"
            " la próxima semana"
        )

    log.info(
        "recomendacion: fuel=%s lat=%.4f lon=%.4f precio_actual=%.3f predicho=%.3f "
        "variacion=%.2f%% veredicto=%s",
        fuel_type,
        lat,
        lon,
        precio_actual,
        precio_predicho,
        variacion_pct,
        veredicto,
    )

    return {
        "veredicto": veredicto,
        "precio_actual": precio_actual,
        "precio_predicho": round(precio_predicho, 3),
        "variacion_pct": variacion_pct,
        "advice": advice,
        "confianza": round(float(artifact.get("r2", 0.0)), 4),
    }
