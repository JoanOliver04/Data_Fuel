"""AI refuel-advice service using the trained Random Forest model.

Replicates EXACTLY the feature ordering of ``FEATURE_COLUMNS`` in
``app.ml.training.entrenar`` so the vector passed to ``model.predict()`` is
identical in shape and column position to what the model saw at training
time. Any divergence here produces garbage predictions.

Feature order (15 columns, must match FEATURE_COLUMNS in entrenar.py):

    distancia, tipo_combustible, dia_de_la_semana, es_festivo,
    precio_semana_anterior, tendencia_ultimos_30_dias, is_low_cost,
    mes, precio_medio_municipio, es_autopista, precio_vs_media_comarca,
    momentum_7d, año, municipio_enc, comarca_enc

The four highest-importance market-context features
(``precio_semana_anterior``, ``precio_medio_municipio``,
``precio_vs_media_comarca``, ``tendencia_ultimos_30_dias`` — together
~74 % of the trained model's decision power) are populated at runtime
from the live ``price_history`` table via
``app.services.historical_features_service``. The two brand-derived
flags (``is_low_cost``, ``es_autopista``) keep their conservative
default of 0 because the recommendation endpoint contract does not
expose a station identifier and the brand / address of the cheapest
station in the user's comarca is therefore not known here.
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import ml_inference_duration_seconds, ml_inference_total
from app.domain.entities.fuel_type import FuelType
from app.ml.data.fuel_type_mapping import FUEL_TYPE_TO_ID
from app.ml.data.holidays import is_festivo
from app.ml.inference.model_loader import get_modelo
from app.services.geopy_distance_service import calcular_distancia_geodesica
from app.services.historical_features_service import (
    comarca_mean_price,
    municipio_mean_price,
    municipio_mean_price_window,
)

log = logging.getLogger(__name__)

_RF_MODEL_LABEL = "recommendation_rf"

_ALZIRA: tuple[float, float] = (39.1496, -0.4373)
_TREND_WINDOW_DAYS: int = 30


def _encode(le: Any, value: str) -> int:
    """Encode a categorical label; falls back to 0 for unseen values."""
    if value in le.classes_:
        return int(le.transform([value])[0])
    log.warning("Label '%s' not in encoder classes — using class 0 as fallback", value)
    return 0


async def generar_recomendacion(
    session: AsyncSession,
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
    last_week = today - timedelta(days=7)

    distancia = calcular_distancia_geodesica(_ALZIRA, (lat, lon))
    tipo_combustible = FUEL_TYPE_TO_ID[fuel_type]
    municipio_enc = _encode(le_municipio, municipio)
    comarca_enc = _encode(le_comarca, comarca)

    # Live historical features.
    #
    # These four read-only aggregate queries currently execute sequentially
    # under `await`. SQLite over aiosqlite serializes all access through a
    # single file-level lock, so `asyncio.gather` would not actually parallelise
    # the work — the tasks would queue on the same lock and incur additional
    # scheduling overhead for zero throughput gain.
    #
    # MIGRATION NOTE (Postgres): when the persistence layer is swapped to a
    # dedicated PostgreSQL engine (MVCC, no global write lock, connection-pool
    # concurrency), lift these four calls into a single
    #     mun_today, mun_last_week, com_today, mun_30d = await asyncio.gather(
    #         municipio_mean_price(session, municipio, fuel_type, today),
    #         municipio_mean_price(session, municipio, fuel_type, last_week),
    #         comarca_mean_price(session, comarca, fuel_type, today),
    #         municipio_mean_price_window(
    #             session, municipio, fuel_type, today, days=_TREND_WINDOW_DAYS,
    #         ),
    #     )
    # to fan-out the I/O. Expected p99 latency reduction: ~3-4x under load.
    municipio_today = await municipio_mean_price(session, municipio, fuel_type, today)
    municipio_last_week = await municipio_mean_price(
        session, municipio, fuel_type, last_week
    )
    comarca_today = await comarca_mean_price(session, comarca, fuel_type, today)
    municipio_30d = await municipio_mean_price_window(
        session, municipio, fuel_type, today, days=_TREND_WINDOW_DAYS
    )

    # Neutral fallbacks keep the feature vector well-defined when the DB has
    # not yet been populated for the requested bucket.
    precio_semana_anterior = (
        municipio_last_week if municipio_last_week is not None else precio_actual
    )
    precio_medio_municipio = (
        municipio_today if municipio_today is not None else precio_actual
    )
    precio_vs_media_comarca = (
        precio_actual - comarca_today if comarca_today is not None else 0.0
    )
    tendencia_ultimos_30_dias = (
        precio_actual - municipio_30d if municipio_30d is not None else 0.0
    )
    momentum_7d = precio_actual - precio_semana_anterior

    features = np.array(
        [[
            distancia,                   # distancia
            tipo_combustible,            # tipo_combustible
            today.weekday(),             # dia_de_la_semana
            is_festivo(today),           # es_festivo
            precio_semana_anterior,      # precio_semana_anterior
            tendencia_ultimos_30_dias,   # tendencia_ultimos_30_dias
            0,                           # is_low_cost (brand unknown at this layer)
            today.month,                 # mes
            precio_medio_municipio,      # precio_medio_municipio
            0,                           # es_autopista (address unknown at this layer)
            precio_vs_media_comarca,     # precio_vs_media_comarca
            momentum_7d,                 # momentum_7d
            today.year,                  # año
            municipio_enc,               # municipio_enc
            comarca_enc,                 # comarca_enc
        ]],
        dtype=float,
    )

    _inference_start = time.perf_counter()
    try:
        precio_predicho = float(model.predict(features)[0])
    except Exception:
        ml_inference_total.labels(model=_RF_MODEL_LABEL, result="error").inc()
        raise
    finally:
        ml_inference_duration_seconds.labels(model=_RF_MODEL_LABEL).observe(
            time.perf_counter() - _inference_start
        )
    ml_inference_total.labels(model=_RF_MODEL_LABEL, result="success").inc()
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
