"""Stations endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.price_history import PricePointOut
from app.api.v1.schemas.station import StationOut
from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.session import get_async_session
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationOut], summary="List gas stations")
async def list_stations(
    province: Annotated[str | None, Query(description="Filter by province (partial match)")] = None,
    municipality: Annotated[
        str | None, Query(description="Filter by municipality (partial match)")
    ] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[StationOut]:
    repo = StationRepository(session)
    stations = await repo.list_all(province=province, municipality=municipality)
    return [StationOut.from_orm_station(s) for s in stations]


@router.get("/{station_id}", response_model=StationOut, summary="Get a single gas station")
async def get_station(
    station_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> StationOut:
    repo = StationRepository(session)
    station = await repo.get_by_id(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return StationOut.from_orm_station(station)


@router.get(
    "/{station_id}/price-history/{fuel_type}",
    response_model=list[PricePointOut],
    summary="Get price history for a station",
)
async def get_price_history(
    station_id: int,
    fuel_type: FuelType,
    days: Annotated[int, Query(ge=1, le=365, description="Look-back window in days")] = 30,
    session: AsyncSession = Depends(get_async_session),
) -> list[PricePointOut]:
    station_repo = StationRepository(session)
    if await station_repo.get_by_id(station_id) is None:
        raise HTTPException(status_code=404, detail="Station not found")
    price_repo = PriceRepository(session)
    rows = await price_repo.get_price_history(station_id, fuel_type, days)
    return [PricePointOut(**row) for row in rows]
