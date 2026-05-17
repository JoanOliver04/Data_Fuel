"""SQLAlchemy repository for vehicle profiles."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.vehicle_profile import VehicleProfileORM


class VehicleProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> VehicleProfileORM:
        profile = VehicleProfileORM(**data)
        self._session.add(profile)
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def get_by_id(self, profile_id: int) -> VehicleProfileORM | None:
        return await self._session.get(VehicleProfileORM, profile_id)

    async def list_all(self) -> Sequence[VehicleProfileORM]:
        result = await self._session.execute(
            select(VehicleProfileORM).order_by(VehicleProfileORM.created_at)
        )
        return result.scalars().all()

    async def update(self, profile: VehicleProfileORM, data: dict[str, Any]) -> VehicleProfileORM:
        for key, value in data.items():
            setattr(profile, key, value)
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def delete(self, profile: VehicleProfileORM) -> None:
        await self._session.delete(profile)
        await self._session.commit()
