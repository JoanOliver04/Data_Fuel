"""Explainable AI (XAI) endpoints.

Two read-only observability endpoints over the trained Random Forest:

* ``GET  /api/v1/xai/global-feature-importance`` — model-wide importance + metadata.
* ``POST /api/v1/xai/explain-recommendation``     — local SHAP explanation + reasoning
  for a single recommendation (same payload as ``POST /predictions/recommendation``).

Both degrade gracefully: a missing model yields 503; a missing/failed SHAP layer
yields a still-useful explanation (global importance + fallback reasoning) rather
than an error. Neither endpoint can affect the recommendation pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.recommendation import RecommendationRequest
from app.api.v1.schemas.xai import (
    ExplainRecommendationResponse,
    FeatureImportanceItem,
    GlobalFeatureImportanceResponse,
    ShapFactor,
)
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.infrastructure.database.session import get_async_session
from app.ml.inference.model_loader import get_modelo
from app.ml.xai import reasoning_engine, shap_explainer
from app.ml.xai.feature_importance_service import (
    FeatureImportance,
    compute_global_importance,
)
from app.ml.xai.feature_metadata import DEFAULT_LOCALE, get_feature_copy
from app.ml.xai.shap_explainer import ShapContribution, ShapExplanation
from app.services.recommendation_service import construir_features, derivar_veredicto

log = logging.getLogger(__name__)

router = APIRouter(prefix="/xai", tags=["xai"])

_TOP_GLOBAL = 10
_TOP_LOCAL = 5


def _to_items(importances: list[FeatureImportance]) -> list[FeatureImportanceItem]:
    return [
        FeatureImportanceItem(
            feature=fi.feature,
            display_name=fi.display_name,
            description=fi.description,
            importance=fi.importance,
        )
        for fi in importances
    ]


def _to_factor(c: ShapContribution, locale: str) -> ShapFactor:
    return ShapFactor(
        feature=c.feature,
        display_name=get_feature_copy(c.feature, locale).label,
        impact=c.impact,
        direction="lowers" if c.impact < 0 else "raises",
    )


@router.get(
    "/global-feature-importance",
    response_model=GlobalFeatureImportanceResponse,
    summary="Global Random Forest feature importance + model metadata",
)
@limiter.limit(lambda: get_settings().xai_rate_limit)
async def global_feature_importance(request: Request) -> GlobalFeatureImportanceResponse:
    artifact = get_modelo()
    if artifact is None:
        raise HTTPException(status_code=503, detail="AI model not loaded")
    try:
        gi = compute_global_importance(artifact, DEFAULT_LOCALE)
    except ValueError as exc:
        log.warning("Global importance unavailable: %s", exc)
        raise HTTPException(
            status_code=503, detail="Feature importance is unavailable for the loaded model"
        ) from exc
    return GlobalFeatureImportanceResponse(
        features=_to_items(gi.features),
        feature_count=gi.feature_count,
        model_trained_at=gi.trained_at,
        model_version=gi.version,
        model_r2=gi.r2,
        model_mae=gi.mae,
    )


def _build_explanation(
    artifact: dict[str, Any],
    vector: Any,
    names: list[str],
    precio_actual: float,
    locale: str,
) -> ExplainRecommendationResponse:
    """Synchronous compute core: predict, SHAP, reasoning, response assembly.

    Runs in a worker thread (CPU-bound: SHAP ~100 ms) so the event loop stays
    responsive. Never raises on SHAP failure — degrades to global-only output.
    """
    model = artifact["model"]
    precio_predicho = float(model.predict(vector)[0])
    veredicto, variacion_pct, _advice = derivar_veredicto(precio_predicho, precio_actual)
    confidence = max(0.0, min(1.0, float(artifact.get("r2", 0.0) or 0.0)))

    # Global top-N (cached) — always available when importances exist.
    try:
        global_items = _to_items(compute_global_importance(artifact, locale).features[:_TOP_GLOBAL])
    except ValueError:
        global_items = []

    # SHAP is gated by XAI_ENABLED: when off (memory-constrained deployments)
    # we skip the local explainer entirely and fall through to the deterministic
    # global-importance + reasoning path below — same graceful branch used when
    # the `shap` dependency is absent.
    explanation: ShapExplanation | None = (
        shap_explainer.explain(model, vector, names)
        if get_settings().xai_enabled
        else None
    )

    if explanation is None:
        reasoning = reasoning_engine.generate_fallback(
            veredicto=veredicto,
            variacion_pct=variacion_pct,
            top_features=[item.feature for item in global_items],
            locale=locale,
        )
        return ExplainRecommendationResponse(
            veredicto=veredicto,
            prediction=round(precio_predicho, 3),
            base_value=round(precio_predicho, 3),
            precio_actual=precio_actual,
            variacion_pct=variacion_pct,
            confidence=round(confidence, 4),
            reasoning=reasoning,
            shap_available=False,
            top_positive_factors=[],
            top_negative_factors=[],
            feature_importance_local=[],
            feature_importance_global=global_items,
        )

    contributions = explanation.contributions  # already sorted by |impact| desc
    local = [_to_factor(c, locale) for c in contributions]
    # "positive" = price-lowering (impact < 0); "negative" = price-raising.
    lowering = [c for c in contributions if c.impact < 0]
    raising = [c for c in contributions if c.impact > 0]
    lowering.sort(key=lambda c: c.impact)          # most negative first
    raising.sort(key=lambda c: c.impact, reverse=True)  # most positive first

    reasoning = reasoning_engine.generate(
        veredicto=veredicto,
        variacion_pct=variacion_pct,
        contributions=contributions,
        locale=locale,
    )
    return ExplainRecommendationResponse(
        veredicto=veredicto,
        prediction=round(precio_predicho, 3),
        base_value=round(explanation.base_value, 3),
        precio_actual=precio_actual,
        variacion_pct=variacion_pct,
        confidence=round(confidence, 4),
        reasoning=reasoning,
        shap_available=True,
        top_positive_factors=[_to_factor(c, locale) for c in lowering[:_TOP_LOCAL]],
        top_negative_factors=[_to_factor(c, locale) for c in raising[:_TOP_LOCAL]],
        feature_importance_local=local,
        feature_importance_global=global_items,
    )


@router.post(
    "/explain-recommendation",
    response_model=ExplainRecommendationResponse,
    summary="Explain a refuel recommendation: SHAP factors + reasoning",
)
@limiter.limit(lambda: get_settings().xai_rate_limit)
async def explain_recommendation(
    request: Request,
    payload: RecommendationRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ExplainRecommendationResponse:
    artifact = get_modelo()
    if artifact is None:
        raise HTTPException(status_code=503, detail="AI model not loaded")

    feats = await construir_features(
        session=session,
        artifact=artifact,
        lat=payload.lat,
        lon=payload.lon,
        fuel_type=payload.fuel_type,
        municipio=payload.municipio,
        comarca=payload.comarca,
        precio_actual=payload.precio_actual,
        station_lat=payload.station_lat,
        station_lon=payload.station_lon,
    )
    # Offload the CPU-bound predict + SHAP to a worker thread.
    return await asyncio.to_thread(
        _build_explanation,
        artifact,
        feats.vector,
        feats.names,
        payload.precio_actual,
        DEFAULT_LOCALE,
    )
