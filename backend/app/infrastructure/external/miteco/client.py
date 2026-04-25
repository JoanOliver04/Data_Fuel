"""Async HTTP client for the MITECO fuel price API.

The MITECO endpoint has three quirks that this client compensates for:

1. TLS handshake — the server only negotiates legacy RSA cipher suites
   (e.g. AES256-GCM-SHA384) that OpenSSL 3 disables at its default
   SECLEVEL=1. We lower SECLEVEL to 0 *for this connection only*, which
   re-enables the cipher; certificate verification stays on.
2. Trust chain — the certificate is signed by 'Firmaprofesional', a Spanish
   CA absent from certifi's bundle. We use the OS trust store via
   `truststore` so verification succeeds on Windows/macOS/Linux.
3. Content type — the body is UTF-8 JSON but the server returns it as
   `text/html` with no charset header. `response.json()` from httpx still
   works because `json.loads` accepts bytes and auto-detects UTF-8.
"""

import json
import logging
import ssl
import time
from types import TracebackType
from typing import Self

import httpx
import truststore

from app.core.config import get_settings
from app.infrastructure.external.miteco.schemas import MitecoApiResponse

log = logging.getLogger(__name__)


class MitecoClientError(RuntimeError):
    """Raised when the MITECO API request fails or returns an unexpected payload."""


class MitecoClient:
    """Async client for the Spanish Ministry's fuel price REST service.

    Usage:
        async with MitecoClient() as client:
            response = await client.get_all_stations()
    """

    _ALL_STATIONS_PATH = "/EstacionesTerrestres/"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.miteco_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.miteco_request_timeout
        self._external_client = client is not None
        self._client: httpx.AsyncClient | None = client

    @staticmethod
    def _build_ssl_context() -> ssl.SSLContext:
        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.set_ciphers("DEFAULT@SECLEVEL=0")
        return ctx

    async def __aenter__(self) -> Self:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Accept": "application/json"},
                verify=self._build_ssl_context(),
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

    async def get_all_stations(self) -> MitecoApiResponse:
        """Fetch every land-based station with current fuel prices."""
        if self._client is None:
            raise MitecoClientError("Client is not initialised. Use 'async with MitecoClient()'.")

        url = f"{self._base_url}{self._ALL_STATIONS_PATH}"
        log.info("MITECO GET %s", url)
        start = time.perf_counter()
        try:
            response = await self._client.get(self._ALL_STATIONS_PATH)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.error("MITECO GET %s failed after %.1fms: %s", url, elapsed_ms, exc)
            raise MitecoClientError(f"MITECO request failed: {exc}") from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        size_kb = len(response.content) / 1024
        log.info(
            "MITECO GET %s → %d (%.1fms, %.1f KB)",
            url,
            response.status_code,
            elapsed_ms,
            size_kb,
        )

        try:
            payload = json.loads(response.content)
            parsed = MitecoApiResponse.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            log.exception("MITECO response parse failed (%.1f KB body)", size_kb)
            raise MitecoClientError(f"Could not parse MITECO response: {exc}") from exc

        log.debug("MITECO parsed %d stations", len(parsed.stations))
        return parsed
