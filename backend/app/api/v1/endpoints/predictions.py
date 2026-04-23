"""Predictions endpoint: 48h price forecast for a given station and fuel type."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.prediction import PredictionOut
from app.domain.entities.fuel_type import FuelType
from app.domain.services.prediction_service import PredictionService, TrainingRow
from app.infrastructure.database.session import get_async_session
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service  # type: ignore[no-any-return]


@router.get(
    "/{station_id}/{fuel_type}",
    response_model=PredictionOut,
    summary="48h price prediction for a station",
)
async def get_prediction(
    station_id: int,
    fuel_type: FuelType,
    session: AsyncSession = Depends(get_async_session),
    prediction_svc: PredictionService = Depends(_get_prediction_service),
) -> PredictionOut:
    station = await StationRepository(session).get_by_id(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    current_price = getattr(station, f"price_{fuel_type}")
    if current_price is None:
        raise HTTPException(
            status_code=404, detail="No current price for this fuel type at this station"
        )

    raw = await PriceRepository(session).get_training_data(fuel_type)
    rows = [TrainingRow(**r) for r in raw]

    result = prediction_svc.predict(
        rows=rows,
        current_price=float(current_price),
        brand=station.brand,
        province=station.province,
        fuel_type=fuel_type,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient training data (need ≥{30} records, got {len(rows)})",
        )

    return PredictionOut.from_result(station_id, fuel_type, result)
