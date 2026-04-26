"""Stations endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.heatmap import (
    HeatmapFeature,
    HeatmapFeatureCollection,
    HeatmapGeometry,
    HeatmapProperties,
)
from app.api.v1.schemas.price_history import PricePointOut
from app.api.v1.schemas.station import StationOut
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import price_for
from app.domain.services.heatmap import HeatmapInput, normalize_prices
from app.infrastructure.database.session import get_async_session
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository

log = logging.getLogger(__name__)

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
    log.debug(
        "stations list: %d results (province=%s, municipality=%s)",
        len(stations),
        province,
        municipality,
    )
    return [StationOut.from_orm_station(s) for s in stations]


@router.get(
    "/heatmap",
    response_model=HeatmapFeatureCollection,
    summary="GeoJSON price heatmap of stations within a radius",
)
async def get_heatmap(
    lat: Annotated[float, Query(ge=-90, le=90, description="Centre latitude (WGS84)")],
    lon: Annotated[float, Query(ge=-180, le=180, description="Centre longitude (WGS84)")],
    radius_km: Annotated[
        float, Query(gt=0, le=200, description="Search radius in kilometres")
    ],
    fuel: Annotated[FuelType, Query(description="Fuel type")],
    session: AsyncSession = Depends(get_async_session),
) -> HeatmapFeatureCollection:
    """Return a lightweight GeoJSON FeatureCollection: one point per station
    inside the radius that sells ``fuel``, with min-max-normalised price.

    Reuses ``StationRepository.find_candidates`` so the bbox + fuel filter
    runs in SQL — no full-table scan, no joins.
    """
    repo = StationRepository(session)
    stations = await repo.find_candidates(
        fuel_type=fuel,
        radius_origin=(lat, lon, radius_km),
    )

    rows: list[HeatmapInput] = []
    for s in stations:
        price = price_for(s, fuel)
        # ``find_candidates`` already excludes NULL-price rows, but a defensive
        # ``price is None`` skip costs nothing and protects against future
        # schema or fuel-type drift.
        if price is None:
            continue
        rows.append(
            HeatmapInput(
                station_id=s.id,
                latitude=s.latitude,
                longitude=s.longitude,
                price=price,
                brand=s.brand,
                name=s.locality,
            )
        )

    points = normalize_prices(rows)
    log.debug(
        "heatmap: lat=%.4f lon=%.4f r=%.1fkm fuel=%s → %d points",
        lat,
        lon,
        radius_km,
        fuel,
        len(points),
    )

    features = [
        HeatmapFeature(
            geometry=HeatmapGeometry(coordinates=(p.longitude, p.latitude)),
            properties=HeatmapProperties(
                id=p.station_id,
                price=p.price,
                price_normalized=p.price_normalized,
                brand=p.brand,
                name=p.name,
            ),
        )
        for p in points
    ]
    return HeatmapFeatureCollection(features=features)


@router.get("/{station_id}", response_model=StationOut, summary="Get a single gas station")
async def get_station(
    station_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> StationOut:
    repo = StationRepository(session)
    station = await repo.get_by_id(station_id)
    if station is None:
        log.info("stations get: station_id=%d not found", station_id)
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
        log.info("price-history: station_id=%d not found", station_id)
        raise HTTPException(status_code=404, detail="Station not found")
    price_repo = PriceRepository(session)
    rows = await price_repo.get_price_history(station_id, fuel_type, days)
    log.debug(
        "price-history: station_id=%d fuel=%s days=%d → %d points",
        station_id,
        fuel_type,
        days,
        len(rows),
    )
    return [PricePointOut(**row) for row in rows]
