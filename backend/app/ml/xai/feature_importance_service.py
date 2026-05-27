"""Global feature importance for the trained Random Forest.

Reads the impurity-based importances that the trainer persists in the model
artifact (``feature_importances`` mapping; falls back to the live estimator's
``feature_importances_`` attribute paired with ``features_names``), normalizes
them to percentages that sum to ~100, sorts descending, and enriches each entry
with human-readable copy from :mod:`app.ml.xai.feature_metadata`.

Results are cached in process memory keyed by the loaded artifact's identity
(``trained_at`` + ``version``), so repeated calls are O(1) and a hot model swap
(:func:`app.ml.inference.model_loader.reload_modelo`) transparently recomputes
on the next call.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

from app.ml.xai.feature_metadata import DEFAULT_LOCALE, get_feature_copy

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeatureImportance:
    """One feature's normalized global importance (percentage 0-100)."""

    feature: str
    importance: float
    display_name: str
    description: str


@dataclass(frozen=True)
class GlobalImportance:
    """Sorted global importances plus the artifact metadata for context."""

    features: list[FeatureImportance]
    trained_at: str | None
    r2: float | None
    mae: float | None
    version: str | None
    feature_count: int


_lock = threading.Lock()
# Single-slot cache: (cache_key, locale) -> computed GlobalImportance.
_cache: dict[tuple[str, str], GlobalImportance] = {}


def _artifact_key(artifact: dict[str, Any]) -> str:
    """Identity that changes whenever a different model is loaded."""
    return f"{artifact.get('version', 'unknown')}|{artifact.get('trained_at', '')}"


def _raw_importances(artifact: dict[str, Any]) -> dict[str, float]:
    """Extract a {feature_name: importance} mapping from the artifact.

    Prefers the persisted ``feature_importances`` dict (authoritative, written
    by the trainer). Falls back to zipping the live estimator's
    ``feature_importances_`` with ``features_names`` for older artifacts.
    Raises ValueError if neither yields a usable, non-empty numeric mapping.
    """
    persisted = artifact.get("feature_importances")
    if isinstance(persisted, dict) and persisted:
        out: dict[str, float] = {}
        for name, value in persisted.items():
            if isinstance(value, (int, float)):
                out[str(name)] = float(value)
        if out:
            return out

    names = artifact.get("features_names") or artifact.get("feature_names")
    model = artifact.get("model")
    raw = getattr(model, "feature_importances_", None)
    if names and raw is not None:
        try:
            values = [float(v) for v in raw]
        except (TypeError, ValueError) as exc:
            raise ValueError("model.feature_importances_ is not numeric") from exc
        if len(values) == len(names):
            return {str(n): v for n, v in zip(names, values, strict=True)}

    raise ValueError("artifact exposes no usable feature importances")


def _normalize_and_sort(
    importances: dict[str, float], locale: str
) -> list[FeatureImportance]:
    """Scale to percentages summing to ~100 and sort descending."""
    total = sum(importances.values())
    # A degenerate (all-zero) importance vector would divide by zero; fall back
    # to a uniform split so the contract (sums to ~100) still holds.
    scale = (100.0 / total) if total > 0 else (100.0 / max(len(importances), 1))
    items = [
        FeatureImportance(
            feature=name,
            importance=round((value * scale) if total > 0 else scale, 4),
            display_name=get_feature_copy(name, locale).label,
            description=get_feature_copy(name, locale).description,
        )
        for name, value in importances.items()
    ]
    items.sort(key=lambda fi: fi.importance, reverse=True)
    return items


def compute_global_importance(
    artifact: dict[str, Any], locale: str = DEFAULT_LOCALE
) -> GlobalImportance:
    """Compute (and cache) global importance for a loaded model artifact.

    Raises ValueError when the artifact exposes no usable importances — callers
    convert that to a 503/graceful-degradation response rather than crashing.
    """
    key = (_artifact_key(artifact), locale)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    with _lock:
        # Re-check under the lock: a concurrent caller may have just filled it.
        cached = _cache.get(key)
        if cached is not None:
            return cached

        features = _normalize_and_sort(_raw_importances(artifact), locale)
        r2 = artifact.get("r2")
        mae = artifact.get("mae")
        result = GlobalImportance(
            features=features,
            trained_at=_as_str_or_none(artifact.get("trained_at")),
            r2=float(r2) if isinstance(r2, (int, float)) else None,
            mae=float(mae) if isinstance(mae, (int, float)) else None,
            version=_as_str_or_none(artifact.get("version")),
            feature_count=len(features),
        )
        _cache[key] = result
        log.debug("Computed global feature importance (%d features, locale=%s)", len(features), locale)
        return result


def _as_str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


def reset_cache() -> None:
    """Clear the memoized importances (used by tests and on model reload)."""
    with _lock:
        _cache.clear()
