"""Numeric ID mapping for FuelType enum values used in ML training and inference."""

from app.domain.entities.fuel_type import FuelType

FUEL_TYPE_TO_ID: dict[FuelType, int] = {
    FuelType.GASOLINA_95: 1,
    FuelType.GASOLINA_95_E10: 2,
    FuelType.GASOLINA_98: 3,
    FuelType.GASOIL: 4,
    FuelType.GASOIL_PREMIUM: 5,
}

ID_TO_FUEL_TYPE: dict[int, FuelType] = {v: k for k, v in FUEL_TYPE_TO_ID.items()}
