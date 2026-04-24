"""Fuel type enumeration."""

from enum import StrEnum


class FuelType(StrEnum):
    """Fuel types tracked by the application."""

    GASOLINA_95 = "gasolina_95"
    GASOLINA_95_E10 = "gasolina_95_e10"
    GASOLINA_98 = "gasolina_98"
    GASOIL = "gasoil"
    GASOIL_PREMIUM = "gasoil_premium"
