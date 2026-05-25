"""Comarca lookups for analytics.

Analytics owns its own loader of the static ``municipio → comarca`` map so the
package stays isolated from the recommendation feature services. Same JSON
source, cached at module level.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_COMARCAS_PATH = Path(__file__).resolve().parents[1] / "ml" / "data" / "comarcas_valencia.json"


@lru_cache(maxsize=1)
def comarca_map() -> dict[str, str]:
    """Cached ``municipio → comarca`` mapping."""
    with _COMARCAS_PATH.open(encoding="utf-8") as fh:
        data: dict[str, str] = json.load(fh)
    return data


def comarca_of(municipio: str) -> str | None:
    """Comarca for a municipio, or None when unmapped."""
    return comarca_map().get(municipio)


@lru_cache(maxsize=1)
def all_comarcas() -> tuple[str, ...]:
    """Sorted tuple of every distinct comarca."""
    return tuple(sorted(set(comarca_map().values())))
