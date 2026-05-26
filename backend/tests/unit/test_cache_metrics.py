"""Unit tests for TTLCache Prometheus instrumentation."""

from app.core.cache import TTLCache
from app.core.metrics import REGISTRY


def _ops(cache: str, result: str) -> float:
    return (
        REGISTRY.get_sample_value(
            "datafuel_cache_operations_total", {"cache": cache, "result": result}
        )
        or 0.0
    )


async def test_hit_miss_set_invalidation_counters() -> None:
    cache: TTLCache[str, str] = TTLCache(ttl_seconds=100.0, name="t_p4")

    miss0 = _ops("t_p4", "miss")
    assert await cache.get("k") is None
    assert _ops("t_p4", "miss") == miss0 + 1.0

    set0 = _ops("t_p4", "set")
    await cache.set("k", "v")
    assert _ops("t_p4", "set") == set0 + 1.0

    hit0 = _ops("t_p4", "hit")
    assert await cache.get("k") == "v"
    assert _ops("t_p4", "hit") == hit0 + 1.0

    inv0 = _ops("t_p4", "invalidation")
    await cache.clear()
    assert _ops("t_p4", "invalidation") == inv0 + 1.0
    assert REGISTRY.get_sample_value("datafuel_cache_entries", {"cache": "t_p4"}) == 0.0


async def test_expiration_counter() -> None:
    cache: TTLCache[str, str] = TTLCache(ttl_seconds=0.0, name="t_p4_exp")
    await cache.set("k", "v")
    exp0 = _ops("t_p4_exp", "expiration")
    assert await cache.get("k") is None  # already expired
    assert _ops("t_p4_exp", "expiration") == exp0 + 1.0


async def test_lru_eviction_bounds_size() -> None:
    cache: TTLCache[str, str] = TTLCache(ttl_seconds=100.0, name="t_lru", max_size=2)
    evict0 = _ops("t_lru", "eviction")

    await cache.set("a", "1")
    await cache.set("b", "2")
    await cache.get("a")  # touch "a" so "b" becomes least-recently-used
    await cache.set("c", "3")  # over capacity → evict LRU ("b")

    assert _ops("t_lru", "eviction") == evict0 + 1.0
    assert cache.size() == 2
    assert await cache.get("b") is None  # evicted
    assert await cache.get("a") == "1"  # survived (recently used)
    assert await cache.get("c") == "3"
