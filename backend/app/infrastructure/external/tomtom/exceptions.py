"""Exceptions raised by the TomTom Matrix Routing client.

The hierarchy lets callers either catch everything via ``TomTomError`` or
react to a specific failure mode (rate limiting, timeout). Mirrors the
single-error pattern of the MITECO/ORS clients but adds two subclasses
because the routing adapter (later phase) treats quota and timeout
failures differently when degrading gracefully to haversine.
"""

from __future__ import annotations


class TomTomError(RuntimeError):
    """Base error: the TomTom API request failed or returned an unexpected payload."""


class TomTomRateLimitError(TomTomError):
    """Raised when TomTom returns HTTP 429 after exhausting retries (quota exceeded)."""


class TomTomTimeoutError(TomTomError):
    """Raised when the request times out after exhausting retries."""
