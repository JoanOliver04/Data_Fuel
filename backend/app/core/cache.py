"""Async-safe in-process TTL cache for hot endpoint results.

Single-instance per logical cache (recommendations, smart-advice, …).
Entries lazily expire on read; the store is bounded by request volume
within the TTL window, which is fine for Data Fuel's traffic profile.

Each instance records Prometheus counters (hit/miss/set/expiration/
invalidation) and an entry-count gauge under its ``name`` label, so cache
behaviour is observable without changing call sites.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Hashable
from typing import Any, Generic, TypeVar

from app.core.metrics import cache_operations_total, cache_size

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Async-safe TTL dict with optional LRU capacity bound.

    The lock serialises store mutations so concurrent requests with the same
    key cannot race a half-written entry. Reads lock too because dict mutations
    happen lazily on expiry.

    Entries expire lazily on read, but on a high-cardinality cache that is only
    fully cleared on an external event (e.g. recommendations, wiped per MITECO
    sync) keys that are never re-read accumulate between clears. ``max_size``
    bounds that growth: once exceeded, the least-recently-used entry is evicted
    on insert. ``None`` (default) keeps the cache unbounded.
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        *,
        name: str = "default",
        max_size: int | None = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._name = name
        self._max_size = max_size
        self._store: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._lock = asyncio.Lock()

    def _record(self, result: str) -> None:
        cache_operations_total.labels(cache=self._name, result=result).inc()

    def _update_size(self) -> None:
        cache_size.labels(cache=self._name).set(len(self._store))

    async def get(self, key: K) -> V | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._record("miss")
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                self._store.pop(key, None)
                self._record("expiration")
                self._record("miss")
                self._update_size()
                return None
            self._store.move_to_end(key)  # mark most-recently-used for LRU
            self._record("hit")
            return value

    async def set(self, key: K, value: V) -> None:
        async with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)
            self._store.move_to_end(key)
            self._record("set")
            if self._max_size is not None:
                while len(self._store) > self._max_size:
                    self._store.popitem(last=False)  # evict least-recently-used
                    self._record("eviction")
            self._update_size()

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
            self._record("invalidation")
            self._update_size()

    def reset(self) -> None:
        """Synchronous wipe — for test fixtures that aren't running in a loop."""
        self._store.clear()
        self._update_size()

    def size(self) -> int:
        return len(self._store)


# Recommendations cache: (params tuple) → list[RecommendationOut]. Cleared
# after every MITECO sync because cached entries embed prices and distances
# that may be stale once new data lands.
recommendations_cache: TTLCache[tuple[Any, ...], list[Any]] = TTLCache(
    ttl_seconds=300.0, name="recommendations", max_size=1024
)
