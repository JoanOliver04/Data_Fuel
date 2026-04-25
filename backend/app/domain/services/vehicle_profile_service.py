"""Pure domain logic for vehicle-profile cost calculations.

Formula:  K (€/km) = (fuel_consumption_per_100km / 100) × fuel_price (€/L)

Edge cases:
  - consumption = 0 (electric vehicle) → K = 0.0
  - Any negative value is rejected by Pydantic before reaching here.
"""

_DEFAULT_REFERENCE_FUEL_PRICE = 1.50  # €/L — used when no live price is available


def compute_km_cost(consumption_l_per_100km: float, fuel_price_eur_per_l: float) -> float:
    """Return vehicle cost per km (€/km) from consumption and fuel price.

    Returns 0.0 for zero-consumption vehicles (electric).
    """
    if consumption_l_per_100km == 0.0:
        return 0.0
    return round((consumption_l_per_100km / 100.0) * fuel_price_eur_per_l, 6)


def default_reference_price() -> float:
    return _DEFAULT_REFERENCE_FUEL_PRICE
