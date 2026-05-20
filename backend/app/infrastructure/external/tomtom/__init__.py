"""TomTom Matrix Routing v2 client package."""

from app.infrastructure.external.tomtom.client import TomTomClient
from app.infrastructure.external.tomtom.exceptions import (
    TomTomError,
    TomTomRateLimitError,
    TomTomTimeoutError,
)
from app.infrastructure.external.tomtom.schemas import (
    GeoPoint,
    MatrixCell,
    MatrixOptions,
    MatrixRequest,
    MatrixResponse,
    MatrixStatistics,
    MatrixWaypoint,
    RouteSummary,
)

__all__ = [
    "GeoPoint",
    "MatrixCell",
    "MatrixOptions",
    "MatrixRequest",
    "MatrixResponse",
    "MatrixStatistics",
    "MatrixWaypoint",
    "RouteSummary",
    "TomTomClient",
    "TomTomError",
    "TomTomRateLimitError",
    "TomTomTimeoutError",
]
