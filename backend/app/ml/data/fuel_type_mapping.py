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

# Legacy/alternate raw strings found in the DB that predate the current enum.
# Maps raw DB string → canonical FuelType so training data stays consistent.
LEGACY_FUEL_TYPE_ALIASES: dict[str, FuelType] = {
    "gasoline_95_e5": FuelType.GASOLINA_95,
    "gasoline_98_e5": FuelType.GASOLINA_98,
    "gasoline_95_e10": FuelType.GASOLINA_95_E10,
    "diesel_a": FuelType.GASOIL,
    "diesel_premium": FuelType.GASOIL_PREMIUM,
}


def resolve_fuel_type(raw: str) -> FuelType | None:
    """Return canonical FuelType for a raw DB string, or None if unrecognised."""
    try:
        return FuelType(raw)
    except ValueError:
        return LEGACY_FUEL_TYPE_ALIASES.get(raw)
