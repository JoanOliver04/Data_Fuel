"""API response schemas for gas stations."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.infrastructure.database.models.station import StationORM


class PricesOut(BaseModel):
    gasoline_95_e5: Decimal | None = None
    gasoline_95_e10: Decimal | None = None
    gasoline_98_e5: Decimal | None = None
    diesel_a: Decimal | None = None
    diesel_premium: Decimal | None = None


class StationOut(BaseModel):
    id: int
    brand: str
    address: str
    locality: str
    municipality: str
    province: str
    postal_code: str
    latitude: float
    longitude: float
    schedule: str
    prices: PricesOut

    @classmethod
    def from_orm_station(cls, orm: StationORM) -> StationOut:
        return cls(
            id=orm.id,
            brand=orm.brand,
            address=orm.address,
            locality=orm.locality,
            municipality=orm.municipality,
            province=orm.province,
            postal_code=orm.postal_code,
            latitude=orm.latitude,
            longitude=orm.longitude,
            schedule=orm.schedule,
            prices=PricesOut(
                gasoline_95_e5=orm.price_gasoline_95_e5,
                gasoline_95_e10=orm.price_gasoline_95_e10,
                gasoline_98_e5=orm.price_gasoline_98_e5,
                diesel_a=orm.price_diesel_a,
                diesel_premium=orm.price_diesel_premium,
            ),
        )
