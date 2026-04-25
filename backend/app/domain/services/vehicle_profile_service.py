"""Pure domain logic for vehicle-profile cost calculations.

Formula:  K (€/km) = (consumption_l_per_100km / 100) × fuel_price (€/L)

The applicable consumption is selected dynamically from the trip distance
(see ``select_consumption_mode``):

    < 5 km           → urban
    5 km ≤ d < 20 km → mixed
    ≥ 20 km          → highway

Edge cases:
  - consumption = 0 (electric vehicle) → K = 0.0
  - Any negative value is rejected by Pydantic before reaching here.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.vehicle_profile import ConsumptionMode, select_consumption_mode

_DEFAULT_REFERENCE_FUEL_PRICE = 1.50  # €/L — used when no live price is available


@dataclass(frozen=True, slots=True)
class ConsumptionProfile:
    """Three-way consumption values used to compute K dynamically per trip."""

    urban: float
    mixed: float
    highway: float

    def consumption_for(self, mode: ConsumptionMode) -> float:
        if mode is ConsumptionMode.URBAN:
            return self.urban
        if mode is ConsumptionMode.HIGHWAY:
            return self.highway
        return self.mixed


def compute_km_cost(consumption_l_per_100km: float, fuel_price_eur_per_l: float) -> float:
    """Return vehicle cost per km (€/km) from consumption and fuel price.

    Returns 0.0 for zero-consumption vehicles (electric).
    """
    if consumption_l_per_100km == 0.0:
        return 0.0
    return round((consumption_l_per_100km / 100.0) * fuel_price_eur_per_l, 6)


def km_cost_for_distance(
    profile: ConsumptionProfile,
    distance_km: float,
    fuel_price_eur_per_l: float,
) -> tuple[float, ConsumptionMode]:
    """Resolve the consumption mode for ``distance_km`` and return (K, mode)."""
    mode = select_consumption_mode(distance_km)
    consumption = profile.consumption_for(mode)
    return compute_km_cost(consumption, fuel_price_eur_per_l), mode


def default_reference_price() -> float:
    return _DEFAULT_REFERENCE_FUEL_PRICE
