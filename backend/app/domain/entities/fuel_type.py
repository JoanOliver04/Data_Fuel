"""Fuel type enumeration."""

from enum import StrEnum


class FuelType(StrEnum):
    """Fuel types tracked by the application.

    Values match the MITECO API field suffixes (English-translated).
    """

    GASOLINE_95_E5 = "gasoline_95_e5"
    GASOLINE_95_E10 = "gasoline_95_e10"
    GASOLINE_98_E5 = "gasoline_98_e5"
    DIESEL_A = "diesel_a"
    DIESEL_PREMIUM = "diesel_premium"
