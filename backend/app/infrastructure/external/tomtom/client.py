"""Async client for the TomTom Matrix Routing v2 API (synchronous endpoint).

Calls ``POST /routing/matrix/2`` with one origin and N destinations to get a
traffic-aware driving distance + duration matrix in a single request. Returns
parsed Pydantic summaries ordered to match the input destinations; converting
those to the routing domain model is the adapter's job (later phase) — this
layer holds no business logic.

Differences from the ORS client, all intentional:
- TomTom's CA is in the standard bundle and it negotiates modern ciphers, so
  (unlike MITECO) no ``truststore`` SSL context is needed.
- The synchronous endpoint accepts up to 2500 cells, far above this project's
  pre-rank cap (≤100 destinations), so there is no chunking.
- Transient failures (429/502/503/504 and timeouts) are retried with
  exponential backoff; ORS does not retry.

Reference (verified May 2026):
    https://developer.tomtom.com/matrix-routing-v2-api/documentation/synchronous-matrix
"""

from __future__ import annotations

import asyncio
import logging
import time
from types import TracebackType
from typing import Self
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.infrastructure.external.tomtom.exceptions import (
    TomTomError,
    TomTomRateLimitError,
    TomTomTimeoutError,
)
from app.infrastructure.external.tomtom.schemas import (
    GeoPoint,
    MatrixOptions,
    MatrixRequest,
    MatrixResponse,
    MatrixWaypoint,
    RouteSummary,
)

log = logging.getLogger(__name__)

_UNSET: object = object()

# Connect/read split within the configurable total timeout. Connecting should
# be quick; the matrix computation itself is what may take a few seconds.
_CONNECT_TIMEOUT_S = 5.0
_READ_TIMEOUT_S = 15.0

# Transient HTTP statuses worth retrying. 429 = quota; 5xx = upstream hiccup.
_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.0  # delays: 1s, 2s, 4s


class TomTomClient:
    """Async client for the TomTom Matrix Routing v2 synchronous endpoint.

    Usage:
        async with TomTomClient() as client:
            summaries = await client.matrix(origin, destinations)
    """

    _MATRIX_PATH = "/routing/matrix/2"

    def __init__(
        self,
        api_key: str | None | object = _UNSET,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
        max_retries: int = _MAX_RETRIES,
        backoff_base: float = _BACKOFF_BASE_S,
    ) -> None:
        settings = get_settings()
        self._api_key: str | None = (
            settings.tomtom_api_key if api_key is _UNSET else api_key  # type: ignore[assignment]
        )
        self._base_url = (base_url or settings.tomtom_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.tomtom_request_timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._external_client = client is not None
        self._client: httpx.AsyncClient | None = client

    def _build_timeout(self) -> httpx.Timeout:
        # Clamp the connect/read phases to the total so a short total stays honoured.
        return httpx.Timeout(
            self._timeout,
            connect=min(_CONNECT_TIMEOUT_S, self._timeout),
            read=min(_READ_TIMEOUT_S, self._timeout),
        )

    async def __aenter__(self) -> Self:
        if self._client is None:
            if not self._api_key:
                raise TomTomError("TOMTOM_API_KEY is not configured")
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._build_timeout(),
                headers={
                    "Accept": "application/json",
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

    async def matrix(
        self,
        origin: tuple[float, float],
        destinations: list[tuple[float, float]],
    ) -> list[RouteSummary | None]:
        """Return one ``RouteSummary`` per destination, ordered to match input.

        Coordinates are ``(latitude, longitude)``. A destination whose cell
        TomTom could not route (``statistics.failures``) yields ``None`` at its
        position; the caller decides how to fall back. Raises ``TomTomError``
        (or a subclass) only on transport, HTTP-status, or schema failures.
        """
        if self._client is None:
            raise TomTomError("Client is not initialised. Use 'async with TomTomClient()'.")
        if not destinations:
            return []

        request = MatrixRequest(
            origins=[MatrixWaypoint(point=GeoPoint(latitude=origin[0], longitude=origin[1]))],
            destinations=[
                MatrixWaypoint(point=GeoPoint(latitude=lat, longitude=lon))
                for lat, lon in destinations
            ],
            options=MatrixOptions(),
        )
        body = request.model_dump(by_alias=True, exclude_none=True)

        req_id = uuid4().hex[:8]
        log.info(
            "TomTom matrix req=%s origin=(%.4f,%.4f) destinations=%d",
            req_id,
            origin[0],
            origin[1],
            len(destinations),
        )

        start = time.perf_counter()
        response = await self._post_with_retry(body, req_id)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if response.status_code == 429:
            log.warning("TomTom matrix req=%s rate-limited (429) after retries", req_id)
            raise TomTomRateLimitError("TomTom rate limit exceeded (429)")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            log.error(
                "TomTom matrix req=%s → %d after %.1fms: %s",
                req_id,
                response.status_code,
                elapsed_ms,
                exc,
            )
            raise TomTomError(f"TomTom request failed: {exc}") from exc

        summaries = self._parse(response, len(destinations), req_id)
        ok = sum(1 for s in summaries if s is not None)
        log.info(
            "TomTom matrix req=%s → %d (%.1fms, %d destinations, %d ok)",
            req_id,
            response.status_code,
            elapsed_ms,
            len(destinations),
            ok,
        )
        return summaries

    async def _post_with_retry(self, body: dict[str, object], req_id: str) -> httpx.Response:
        """POST the matrix, retrying transient failures with exponential backoff.

        Returns the final response (which may still carry a retryable status if
        retries were exhausted — the caller maps that to an error). Raises
        ``TomTomTimeoutError`` / ``TomTomError`` for timeout / transport
        failures that survive all retries.
        """
        assert self._client is not None
        params = {"key": self._api_key}
        response: httpx.Response | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(self._MATRIX_PATH, params=params, json=body)
            except httpx.TimeoutException as exc:
                if attempt < self._max_retries:
                    delay = self._backoff(attempt)
                    log.warning(
                        "TomTom matrix req=%s timeout, retry %d/%d after %.1fs",
                        req_id,
                        attempt + 1,
                        self._max_retries,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise TomTomTimeoutError(f"TomTom request timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                raise TomTomError(f"TomTom request failed: {exc}") from exc

            if response.status_code in _RETRYABLE_STATUSES and attempt < self._max_retries:
                delay = self._retry_delay(response, attempt)
                log.warning(
                    "TomTom matrix req=%s status=%d, retry %d/%d after %.1fs",
                    req_id,
                    response.status_code,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            return response

        # Loop only falls through here if the last attempt was a retryable
        # status (retries exhausted); response is guaranteed set by then.
        assert response is not None
        return response

    def _backoff(self, attempt: int) -> float:
        """Exponential backoff for ``attempt`` (0-based): base·2ⁿ → 1s, 2s, 4s."""
        return self._backoff_base * float(2**attempt)

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Backoff for the next retry; honour ``Retry-After`` if TomTom sends it."""
        retry_after: str | None = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                seconds = float(retry_after)
            except ValueError:
                seconds = None
            if seconds is not None:
                return max(0.0, seconds)
        return self._backoff(attempt)

    def _parse(
        self,
        response: httpx.Response,
        n_destinations: int,
        req_id: str,
    ) -> list[RouteSummary | None]:
        """Validate the body and order summaries by destination index."""
        try:
            parsed = MatrixResponse.model_validate(response.json())
        except (ValueError, TypeError) as exc:
            log.exception("TomTom matrix req=%s response parse failed", req_id)
            raise TomTomError(f"Could not parse TomTom response: {exc}") from exc

        summaries: list[RouteSummary | None] = [None] * n_destinations
        for cell in parsed.data:
            if cell.origin_index == 0 and 0 <= cell.destination_index < n_destinations:
                summaries[cell.destination_index] = cell.route_summary
        return summaries
