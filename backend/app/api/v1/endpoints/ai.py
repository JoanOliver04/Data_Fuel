"""Conversational AI endpoints.

These enrich the platform's deterministic outputs with LLM-generated prose. They
gather already-computed facts (ranking, prediction, trends) from existing domain
services, then hand them to the explanation engine — which degrades to a
deterministic explanation whenever the LLM is unavailable. LLM failures never
affect the underlying recommendation/prediction endpoints.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.ai.safety import sanitize_question
from app.ai.schemas import (
    AIExplanation,
    AIProviderHealth,
    ChatRequest,
    PredictionFact,
    RecommendationFacts,
    StationFact,
    TrendFacts,
    TrendSummary,
    Verdict,
)
from app.ai.services import explain, summarize_trend
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import StationCost, rank_stations
from app.domain.services.prediction_service import (
    PredictionResult,
    PredictionService,
    TrainingRow,
)
from app.infrastructure.database.session import get_async_session
from app.ml.inference.model_loader import get_modelo
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository
from app.services.historical_features_service import (
    comarca_mean_price,
    municipio_mean_price,
)

log = logging.getLogger("app.ai.endpoints")

router = APIRouter(prefix="/ai", tags=["ai"])

_MAX_FACT_STATIONS = 3
_VERDICT_THRESHOLD_PCT = 0.5


def _get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service  # type: ignore[no-any-return]


def _model_version() -> str:
    artifact = get_modelo()
    if artifact is None:
        return "none"
    return f"{artifact.get('version', 'unknown')}|{artifact.get('trained_at', '')}"


def _verdict_and_confidence(prediction: PredictionResult | None) -> tuple[Verdict, float]:
    if prediction is None:
        return "NEUTRAL", 0.3
    confidence = max(0.0, min(1.0, prediction.model_r2))
    if prediction.change_pct <= -_VERDICT_THRESHOLD_PCT:
        return "WAIT", confidence
    if prediction.change_pct >= _VERDICT_THRESHOLD_PCT:
        return "REFUEL_NOW", confidence
    return "NEUTRAL", confidence


def _station_facts(ranked: list[StationCost]) -> list[StationFact]:
    return [
        StationFact(
            rank=i + 1,
            brand=sc.brand,
            locality=sc.locality,
            price_per_liter=float(sc.price_per_liter),
            distance_km=sc.distance_km,
            total_cost=float(sc.total_cost),
            driving_duration_min=sc.driving_duration_min,
            traffic_delay_seconds=sc.traffic_delay_seconds,
        )
        for i, sc in enumerate(ranked[:_MAX_FACT_STATIONS])
    ]


async def _build_facts(
    session: AsyncSession,
    prediction_svc: PredictionService,
    settings: Settings,
    *,
    lat: float,
    lon: float,
    fuel_type: FuelType,
    liters: float,
    km_cost: float | None,
    max_distance_km: float | None,
    municipio: str | None,
    comarca: str | None,
) -> RecommendationFacts | None:
    """Gather ranking + prediction into engine-ready facts. None if no stations."""
    effective_km_cost = km_cost if km_cost is not None else settings.default_km_cost
    stations = await StationRepository(session).list_all()
    ranked = rank_stations(
        stations=stations,
        fuel_type=fuel_type,
        user_lat=lat,
        user_lon=lon,
        liters=liters,
        km_cost=effective_km_cost,
        max_distance_km=max_distance_km,
        limit=_MAX_FACT_STATIONS,
    )
    if not ranked:
        return None

    best = ranked[0]
    # Skip the (potentially huge) training-data load when a fresh model is
    # cached; predict() only needs rows on a cold/stale cache.
    rows: list[TrainingRow] = []
    if not prediction_svc.has_fresh_model(fuel_type):
        raw = await PriceRepository(session).get_training_data(fuel_type)
        rows = [TrainingRow(**r) for r in raw]
    # Training + inference are CPU-bound and synchronous; run them in a worker
    # thread so they never block the event loop (and starve other requests).
    prediction = await asyncio.to_thread(
        prediction_svc.predict,
        rows=rows,
        current_price=float(best.price_per_liter),
        brand=best.brand,
        province=best.province,
        fuel_type=fuel_type,
    )
    verdict, confidence = _verdict_and_confidence(prediction)
    prediction_fact = (
        PredictionFact(
            current_price=prediction.current_price,
            predicted_price=prediction.predicted_price,
            variation_pct=prediction.change_pct,
            horizon_hours=prediction.horizon_hours,
            confidence=confidence,
            model_r2=prediction.model_r2,
        )
        if prediction is not None
        else None
    )
    return RecommendationFacts(
        fuel_type=fuel_type.value,
        municipio=municipio,
        comarca=comarca,
        liters=liters,
        km_cost=effective_km_cost,
        stations=_station_facts(ranked),
        prediction=prediction_fact,
        verdict=verdict,
        confidence=confidence,
        model_version=_model_version(),
    )


@router.get(
    "/explain-recommendation",
    response_model=AIExplanation,
    summary="Conversational explanation of the top recommendation",
)
@limiter.limit(lambda: get_settings().ai_rate_limit)
async def explain_recommendation(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    fuel_type: Annotated[FuelType, Query()],
    liters: Annotated[float, Query(gt=0, le=200)] = 50.0,
    km_cost: Annotated[float | None, Query(ge=0)] = None,
    max_distance_km: Annotated[float | None, Query(ge=0)] = 20.0,
    municipio: Annotated[str | None, Query(max_length=120)] = None,
    comarca: Annotated[str | None, Query(max_length=120)] = None,
    session: AsyncSession = Depends(get_async_session),
    prediction_svc: PredictionService = Depends(_get_prediction_service),
) -> AIExplanation:
    settings = get_settings()
    facts = await _build_facts(
        session, prediction_svc, settings, lat=lat, lon=lon, fuel_type=fuel_type,
        liters=liters, km_cost=km_cost, max_distance_km=max_distance_km,
        municipio=municipio, comarca=comarca,
    )
    if facts is None:
        raise HTTPException(status_code=404, detail="No stations found in the search area")
    return await explain("recommendation", facts, get_llm_provider(settings))


@router.get(
    "/explain-prediction",
    response_model=AIExplanation,
    summary="Conversational explanation of the price prediction",
)
@limiter.limit(lambda: get_settings().ai_rate_limit)
async def explain_prediction(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    fuel_type: Annotated[FuelType, Query()],
    liters: Annotated[float, Query(gt=0, le=200)] = 50.0,
    km_cost: Annotated[float | None, Query(ge=0)] = None,
    max_distance_km: Annotated[float | None, Query(ge=0)] = 20.0,
    session: AsyncSession = Depends(get_async_session),
    prediction_svc: PredictionService = Depends(_get_prediction_service),
) -> AIExplanation:
    settings = get_settings()
    facts = await _build_facts(
        session, prediction_svc, settings, lat=lat, lon=lon, fuel_type=fuel_type,
        liters=liters, km_cost=km_cost, max_distance_km=max_distance_km,
        municipio=None, comarca=None,
    )
    if facts is None:
        raise HTTPException(status_code=404, detail="No stations found in the search area")
    return await explain("prediction", facts, get_llm_provider(settings))


@router.get(
    "/trend-summary",
    response_model=TrendSummary,
    summary="Conversational price-trend summary for an area",
)
@limiter.limit(lambda: get_settings().ai_rate_limit)
async def trend_summary(
    request: Request,
    fuel_type: Annotated[FuelType, Query()],
    municipio: Annotated[str | None, Query(max_length=120)] = None,
    comarca: Annotated[str | None, Query(max_length=120)] = None,
    session: AsyncSession = Depends(get_async_session),
) -> TrendSummary:
    if not municipio and not comarca:
        raise HTTPException(status_code=422, detail="Provide 'municipio' or 'comarca'")
    settings = get_settings()
    today = date.today()
    last_week = today - timedelta(days=7)
    if comarca:
        area_name = comarca
        today_price = await comarca_mean_price(session, comarca, fuel_type, today)
        prev_price = await comarca_mean_price(session, comarca, fuel_type, last_week)
    else:
        assert municipio is not None
        area_name = municipio
        today_price = await municipio_mean_price(session, municipio, fuel_type, today)
        prev_price = await municipio_mean_price(session, municipio, fuel_type, last_week)

    delta_pct: float | None = None
    direction: Literal["UP", "DOWN", "STABLE"] = "STABLE"
    if today_price is not None and prev_price is not None and prev_price > 0:
        delta_pct = round((today_price - prev_price) / prev_price * 100, 2)
        if delta_pct <= -0.3:
            direction = "DOWN"
        elif delta_pct >= 0.3:
            direction = "UP"
    facts = TrendFacts(
        fuel_type=fuel_type.value,
        area_name=area_name,
        mean_price_today=today_price,
        mean_price_last_week=prev_price,
        delta_pct=delta_pct,
        direction=direction,
    )
    return await summarize_trend(facts, get_llm_provider(settings))


@router.post(
    "/chat",
    response_model=AIExplanation,
    summary="Ask a question about the recommendation in this context",
)
@limiter.limit(lambda: get_settings().ai_rate_limit)
async def chat(
    request: Request,
    body: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    prediction_svc: PredictionService = Depends(_get_prediction_service),
) -> AIExplanation:
    settings = get_settings()
    try:
        fuel_type = FuelType(body.fuel_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid fuel_type") from exc

    question = sanitize_question(body.question, settings.llm_max_input_chars)
    if not question:
        raise HTTPException(status_code=422, detail="Empty question after sanitisation")

    facts = await _build_facts(
        session, prediction_svc, settings, lat=body.lat, lon=body.lon, fuel_type=fuel_type,
        liters=body.liters, km_cost=None, max_distance_km=20.0,
        municipio=body.municipio, comarca=body.comarca,
    )
    if facts is None:
        raise HTTPException(status_code=404, detail="No stations found in the search area")
    return await explain("chat", facts, get_llm_provider(settings), question=question)


@router.get(
    "/health",
    response_model=AIProviderHealth,
    summary="LLM provider liveness (diagnostic — does not gate serving)",
)
@limiter.limit(lambda: get_settings().ai_rate_limit)
async def ai_provider_health(request: Request) -> AIProviderHealth:
    settings = get_settings()
    provider = get_llm_provider(settings)
    health = await provider.health_check()
    return AIProviderHealth(
        configured_provider=settings.llm_provider,
        active_provider=health.provider,
        healthy=health.healthy,
        detail=health.detail,
    )
