"""Geodesic distance calculation using geopy (WGS-84 ellipsoid).

Distinct from cost_calculator's haversine: haversine for fast mass ranking,
geodesic for accurate single-point inference in the ML pipeline.
"""

from __future__ import annotations

from geopy.distance import geodesic


def calcular_distancia_geodesica(
    coord_a: tuple[float, float],
    coord_b: tuple[float, float],
) -> float:
    """Geodesic distance in km between two (lat, lon) points (WGS-84)."""
    return geodesic(coord_a, coord_b).km
