"""Async-safe in-process TTL cache for hot endpoint results.

Single-instance per logical cache (recommendations, smart-advice, …).
Entries lazily expire on read; the store is bounded by request volume
within the TTL window, which is fine for Data Fuel's traffic profile.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Hashable
from typing import Any, Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Async-safe TTL dict.

    The lock serialises store mutations so concurrent requests with the same
    key cannot race a half-written entry. Reads lock too because dict mutations
    happen lazily on expiry.
    """

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[K, tuple[float, V]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: K) -> V | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: K, value: V) -> None:
        async with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def reset(self) -> None:
        """Synchronous wipe — for test fixtures that aren't running in a loop."""
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


# Recommendations cache: (params tuple) → list[RecommendationOut]. Cleared
# after every MITECO sync because cached entries embed prices and distances
# that may be stale once new data lands.
recommendations_cache: TTLCache[tuple[Any, ...], list[Any]] = TTLCache(ttl_seconds=300.0)
