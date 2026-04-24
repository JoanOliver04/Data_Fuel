"""Smart refuelling advisor endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.smart_advice import SmartAdviceOut
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import rank_stations
from app.domain.services.prediction_service import PredictionService, TrainingRow
from app.domain.services.smart_refuel_service import SmartRefuelService
from app.infrastructure.database.session import get_async_session
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository

router = APIRouter(prefix="/smart-advice", tags=["smart-advice"])

_smart_refuel_svc = SmartRefuelService()


def _get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service  # type: ignore[no-any-return]


@router.get("", response_model=SmartAdviceOut, summary="Smart refuelling recommendation")
@limiter.limit(lambda: get_settings().predictions_rate_limit)
async def get_smart_advice(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    fuel_type: Annotated[FuelType, Query()],
    liters: Annotated[float, Query(gt=0, le=200)] = 50.0,
    km_cost: Annotated[float | None, Query(ge=0)] = None,
    max_distance_km: Annotated[float | None, Query(ge=0)] = 20.0,
    session: AsyncSession = Depends(get_async_session),
    prediction_svc: PredictionService = Depends(_get_prediction_service),
) -> SmartAdviceOut:
    settings = get_settings()
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
        limit=1,
    )
    if not ranked:
        raise HTTPException(status_code=404, detail="No stations found in the search area")

    best = ranked[0]

    raw = await PriceRepository(session).get_training_data(fuel_type)
    rows = [TrainingRow(**r) for r in raw]

    prediction = prediction_svc.predict(
        rows=rows,
        current_price=float(best.price_per_liter),
        brand=best.brand,
        province=best.province,
        fuel_type=fuel_type,
    )

    advice = _smart_refuel_svc.advise(
        best_station=best,
        prediction=prediction,
        liters=liters,
        km_cost=effective_km_cost,
    )
    return SmartAdviceOut.from_advice(advice)
