"""Vehicle profiles endpoints: CRUD + km-cost estimator."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.vehicle_profile import (
    KmCostEstimate,
    VehicleProfileCreate,
    VehicleProfileOut,
    VehicleProfileUpdate,
)
from app.domain.services.vehicle_profile_service import compute_km_cost
from app.infrastructure.database.session import get_async_session
from app.repositories.vehicle_profile_repository import VehicleProfileRepository

router = APIRouter(prefix="/vehicle-profiles", tags=["vehicle-profiles"])


@router.get(
    "/estimate-km-cost",
    response_model=KmCostEstimate,
    summary="Preview €/km from consumption",
)
async def estimate_km_cost(
    consumption: Annotated[float, Query(ge=0.0, le=50.0, description="Fuel consumption (L/100km)")],
    fuel_price: Annotated[float, Query(gt=0.0, le=10.0, description="Fuel price (€/L)")],
) -> KmCostEstimate:
    return KmCostEstimate(
        consumption_l_per_100km=consumption,
        fuel_price_eur_per_l=fuel_price,
        km_cost_eur_per_km=compute_km_cost(consumption, fuel_price),
    )


@router.get("", response_model=list[VehicleProfileOut], summary="List all vehicle profiles")
async def list_vehicle_profiles(
    session: AsyncSession = Depends(get_async_session),
) -> list[VehicleProfileOut]:
    profiles = await VehicleProfileRepository(session).list_all()
    return [VehicleProfileOut.model_validate(p) for p in profiles]


@router.post(
    "",
    response_model=VehicleProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create vehicle profile",
)
async def create_vehicle_profile(
    body: VehicleProfileCreate,
    session: AsyncSession = Depends(get_async_session),
) -> VehicleProfileOut:
    # Reference K stored for display uses the mixed consumption (combined default).
    km_cost = compute_km_cost(body.fuel_consumption_mixed, body.reference_fuel_price)
    data = {
        "name": body.name,
        "fuel_consumption_urban": body.fuel_consumption_urban,
        "fuel_consumption_mixed": body.fuel_consumption_mixed,
        "fuel_consumption_highway": body.fuel_consumption_highway,
        "tank_capacity_litres": body.tank_capacity_litres,
        "driving_style": body.driving_style.value,
        "km_cost_per_km": km_cost,
    }
    profile = await VehicleProfileRepository(session).create(data)
    return VehicleProfileOut.model_validate(profile)


@router.get("/{profile_id}", response_model=VehicleProfileOut, summary="Get vehicle profile")
async def get_vehicle_profile(
    profile_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> VehicleProfileOut:
    profile = await VehicleProfileRepository(session).get_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Vehicle profile not found")
    return VehicleProfileOut.model_validate(profile)


@router.put("/{profile_id}", response_model=VehicleProfileOut, summary="Update vehicle profile")
async def update_vehicle_profile(
    profile_id: int,
    body: VehicleProfileUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> VehicleProfileOut:
    repo = VehicleProfileRepository(session)
    profile = await repo.get_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Vehicle profile not found")

    updates: dict = body.model_dump(exclude_none=True, exclude={"reference_fuel_price"})
    if "driving_style" in updates:
        updates["driving_style"] = body.driving_style.value if body.driving_style else None

    # Recompute km_cost_per_km when mixed consumption or reference price changes.
    consumption_changed = body.fuel_consumption_mixed is not None
    if consumption_changed or body.reference_fuel_price is not None:
        new_mixed = (
            body.fuel_consumption_mixed
            if body.fuel_consumption_mixed is not None
            else profile.fuel_consumption_mixed
        )
        ref_price = body.reference_fuel_price or 1.50
        updates["km_cost_per_km"] = compute_km_cost(new_mixed, ref_price)

    profile = await repo.update(profile, updates)
    return VehicleProfileOut.model_validate(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete vehicle profile",
)
async def delete_vehicle_profile(
    profile_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    repo = VehicleProfileRepository(session)
    profile = await repo.get_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Vehicle profile not found")
    await repo.delete(profile)
