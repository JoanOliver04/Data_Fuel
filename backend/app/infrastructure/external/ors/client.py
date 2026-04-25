"""Async client for the OpenRouteService Matrix API.

Calls `POST /v2/matrix/driving-car` with one origin and N destinations to
get driving distance (km) and duration (min) in a single batch. Batches
larger than `chunk_size` destinations are split and concatenated.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Self

import httpx

from app.core.config import get_settings

_UNSET: object = object()


class ORSClientError(RuntimeError):
    """Raised when the ORS API request fails or returns an unexpected payload."""


@dataclass(frozen=True, slots=True)
class ORSMatrixResult:
    """Per-destination driving distance and duration relative to one origin."""

    distance_km: float
    duration_min: float


class ORSClient:
    """Async client for the OpenRouteService Matrix API.

    Usage:
        async with ORSClient() as client:
            results = await client.driving_matrix(origin, destinations)
    """

    _MATRIX_PATH = "/v2/matrix/driving-car"

    def __init__(
        self,
        api_key: str | None | object = _UNSET,
        base_url: str | None = None,
        timeout: float | None = None,
        chunk_size: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key: str | None = (
            settings.ors_api_key if api_key is _UNSET else api_key  # type: ignore[assignment]
        )
        self._base_url = (base_url or settings.ors_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.ors_request_timeout
        self._chunk_size = chunk_size if chunk_size is not None else settings.ors_matrix_chunk_size
        self._external_client = client is not None
        self._client: httpx.AsyncClient | None = client

    async def __aenter__(self) -> Self:
        if self._client is None:
            if not self._api_key:
                raise ORSClientError("ORS_API_KEY is not configured")
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "Authorization": self._api_key,
                    "Accept": "application/json, application/geo+json",
                    "Content-Type": "application/json",
                },
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self._external_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def driving_matrix(
        self,
        origin: tuple[float, float],
        destinations: list[tuple[float, float]],
    ) -> list[ORSMatrixResult]:
        """Return driving (distance_km, duration_min) from `origin` to each destination.

        Coordinates are `(latitude, longitude)`. ORS expects `[lon, lat]`.
        Splits destinations into chunks of `chunk_size` to respect API limits.
        """
        if self._client is None:
            raise ORSClientError("Client is not initialised. Use 'async with ORSClient()'.")
        if not destinations:
            return []

        results: list[ORSMatrixResult] = []
        for start in range(0, len(destinations), self._chunk_size):
            chunk = destinations[start : start + self._chunk_size]
            results.extend(await self._matrix_chunk(origin, chunk))
        return results

    async def _matrix_chunk(
        self,
        origin: tuple[float, float],
        destinations: list[tuple[float, float]],
    ) -> list[ORSMatrixResult]:
        assert self._client is not None

        locations = [[origin[1], origin[0]]] + [[lon, lat] for lat, lon in destinations]
        payload: dict[str, object] = {
            "locations": locations,
            "sources": [0],
            "destinations": list(range(1, len(locations))),
            "metrics": ["distance", "duration"],
            "units": "km",
        }

        try:
            response = await self._client.post(self._MATRIX_PATH, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ORSClientError(f"ORS request failed: {exc}") from exc

        try:
            data = response.json()
            distances = data["distances"][0]
            durations = data["durations"][0]
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            raise ORSClientError(f"Could not parse ORS response: {exc}") from exc

        if len(distances) != len(destinations) or len(durations) != len(destinations):
            raise ORSClientError("ORS response length mismatch with destinations")

        return [
            ORSMatrixResult(
                distance_km=float(d) if d is not None else float("inf"),
                duration_min=(float(t) / 60.0) if t is not None else float("inf"),
            )
            for d, t in zip(distances, durations, strict=True)
        ]
