"""Predictions endpoint: 48h Ridge forecast + AI RF refuel-advice."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.prediction import PredictionOut
from app.api.v1.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.services.prediction_service import PredictionService, TrainingRow
from app.infrastructure.database.session import get_async_session
from app.ml.inference.model_loader import get_modelo
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository
from app.services.recommendation_service import generar_recomendacion

log = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])

# Maps FuelType enum values to the corresponding StationORM attribute name.
# Explicit mapping needed because ORM column names predate the enum refactor.
_FUEL_PRICE_ATTR: dict[FuelType, str] = {
    FuelType.GASOLINA_95: "price_gasoline_95_e5",
    FuelType.GASOLINA_95_E10: "price_gasoline_95_e10",
    FuelType.GASOLINA_98: "price_gasoline_98_e5",
    FuelType.GASOIL: "price_diesel_a",
    FuelType.GASOIL_PREMIUM: "price_diesel_premium",
}


def _get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service  # type: ignore[no-any-return]


@router.get(
    "/{station_id}/{fuel_type}",
    response_model=PredictionOut,
    summary="48h price prediction for a station",
)
@limiter.limit(lambda: get_settings().predictions_rate_limit)
async def get_prediction(
    request: Request,
    station_id: int,
    fuel_type: FuelType,
    session: AsyncSession = Depends(get_async_session),
    prediction_svc: PredictionService = Depends(_get_prediction_service),
) -> PredictionOut:
    log.debug("predictions: station_id=%d fuel=%s", station_id, fuel_type)
    station = await StationRepository(session).get_by_id(station_id)
    if station is None:
        log.info("predictions: station_id=%d not found", station_id)
        raise HTTPException(status_code=404, detail="Station not found")

    current_price = getattr(station, _FUEL_PRICE_ATTR[fuel_type])
    if current_price is None:
        log.info(
            "predictions: station_id=%d has no current price for fuel=%s",
            station_id,
            fuel_type,
        )
        raise HTTPException(
            status_code=404, detail="No current price for this fuel type at this station"
        )

    raw = await PriceRepository(session).get_training_data(fuel_type)
    rows = [TrainingRow(**r) for r in raw]
    log.debug("predictions: %d training rows for fuel=%s", len(rows), fuel_type)

    result = prediction_svc.predict(
        rows=rows,
        current_price=float(current_price),
        brand=station.brand,
        province=station.province,
        fuel_type=fuel_type,
    )
    if result is None:
        log.warning(
            "predictions: insufficient training data for fuel=%s (got %d, need ≥30)",
            fuel_type,
            len(rows),
        )
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient training data (need ≥{30} records, got {len(rows)})",
        )

    return PredictionOut.from_result(station_id, fuel_type, result)


@router.post(
    "/recommendation",
    response_model=RecommendationResponse,
    summary="AI refuel-advice: refuel now or wait?",
)
@limiter.limit("5/minute")
async def post_recommendation(
    request: Request,
    payload: RecommendationRequest,
    session: AsyncSession = Depends(get_async_session),
) -> RecommendationResponse:
    if get_modelo() is None:
        raise HTTPException(status_code=503, detail="AI model not loaded")
    result = await generar_recomendacion(
        session=session,
        lat=payload.lat,
        lon=payload.lon,
        fuel_type=payload.fuel_type,
        municipio=payload.municipio,
        comarca=payload.comarca,
        precio_actual=payload.precio_actual,
    )
    return RecommendationResponse(**result)
