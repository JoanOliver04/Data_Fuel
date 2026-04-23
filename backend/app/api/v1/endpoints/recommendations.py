"""Recommendations endpoint: cheapest stations ranked by total refuelling cost."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.recommendation import RecommendationOut
from app.core.config import get_settings
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import rank_stations
from app.infrastructure.database.session import get_async_session
from app.repositories.station_repository import StationRepository

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationOut], summary="Rank stations by total cost")
async def get_recommendations(
    lat: Annotated[float, Query(ge=-90, le=90, description="User latitude (WGS84)")],
    lon: Annotated[float, Query(ge=-180, le=180, description="User longitude (WGS84)")],
    liters: Annotated[float, Query(gt=0, le=200, description="Litres to refuel")],
    fuel_type: Annotated[FuelType, Query(description="Fuel type")],
    limit: Annotated[int, Query(ge=1, le=50, description="Max results")] = 10,
    km_cost: Annotated[
        float | None, Query(ge=0, description="Vehicle cost per km (€/km)")
    ] = None,
    max_distance_km: Annotated[
        float | None, Query(ge=0, description="Exclude stations beyond this distance")
    ] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[RecommendationOut]:
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
        limit=limit,
    )
    return [RecommendationOut.from_station_cost(sc) for sc in ranked]
