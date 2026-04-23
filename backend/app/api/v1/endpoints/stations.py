"""Stations endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.station import StationOut
from app.infrastructure.database.session import get_async_session
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
