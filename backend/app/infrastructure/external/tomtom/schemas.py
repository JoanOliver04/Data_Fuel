"""Pydantic schemas mirroring the TomTom Matrix Routing v2 wire shapes.

TomTom uses camelCase JSON keys; these models alias them to snake_case
Python attributes (same pattern as the MITECO schemas). Request bodies are
serialised with ``model_dump(by_alias=True, exclude_none=True)`` so only the
fields TomTom expects are emitted, in the casing it expects.

Reference (verified May 2026):
    POST https://api.tomtom.com/routing/matrix/2?key=<key>
    https://developer.tomtom.com/matrix-routing-v2-api/documentation/synchronous-matrix

Only the fields this project consumes are modelled; ``extra="ignore"`` drops
the rest so additive TomTom changes do not break parsing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ── Request ──────────────────────────────────────────────────────────────────


class GeoPoint(BaseModel):
    """A WGS84 coordinate as TomTom expects it (lowercase keys, no alias)."""

    latitude: float
    longitude: float


class MatrixWaypoint(BaseModel):
    """One origin or destination entry: ``{"point": {...}}``."""

    point: GeoPoint


class MatrixOptions(BaseModel):
    """Routing options. Defaults give a traffic-aware fastest-by-car matrix.

    ``departAt="now"`` is what makes the result traffic-aware; ``traffic="live"``
    enables live-traffic travel times. Matrix v2 is summary-only by design, so
    there is no geometry/representation option to disable.
    """

    model_config = ConfigDict(populate_by_name=True)

    depart_at: str = Field(default="now", alias="departAt")
    route_type: str = Field(default="fastest", alias="routeType")
    traffic: str = Field(default="live")
    travel_mode: str = Field(default="car", alias="travelMode")


class MatrixRequest(BaseModel):
    """Full synchronous-matrix request body."""

    model_config = ConfigDict(populate_by_name=True)

    origins: list[MatrixWaypoint]
    destinations: list[MatrixWaypoint]
    options: MatrixOptions = Field(default_factory=MatrixOptions)


# ── Response ─────────────────────────────────────────────────────────────────


class RouteSummary(BaseModel):
    """Per-cell route summary. ``trafficDelayInSeconds`` is the TomTom edge:
    seconds of delay versus free-flow. Time fields are absent when
    ``departAt``/``arriveAt`` is ``"any"``."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    length_in_meters: int = Field(alias="lengthInMeters")
    travel_time_in_seconds: int = Field(alias="travelTimeInSeconds")
    traffic_delay_in_seconds: int | None = Field(default=None, alias="trafficDelayInSeconds")
    departure_time: str | None = Field(default=None, alias="departureTime")
    arrival_time: str | None = Field(default=None, alias="arrivalTime")


class MatrixCell(BaseModel):
    """One cell of the flat ``data`` array, indexed by origin/destination.

    ``route_summary`` is optional: a failed cell (TomTom ``statistics.failures``)
    carries no summary, and the routing adapter falls back per leg.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    origin_index: int = Field(alias="originIndex")
    destination_index: int = Field(alias="destinationIndex")
    route_summary: RouteSummary | None = Field(default=None, alias="routeSummary")


class MatrixStatistics(BaseModel):
    """Aggregate success/failure counts returned alongside the matrix."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    total_count: int = Field(default=0, alias="totalCount")
    successes: int = 0
    failures: int = 0


class MatrixResponse(BaseModel):
    """Top-level synchronous-matrix response wrapper."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    data: list[MatrixCell] = Field(default_factory=list)
    statistics: MatrixStatistics | None = None
