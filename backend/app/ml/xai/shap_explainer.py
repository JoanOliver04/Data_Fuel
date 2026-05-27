"""Process-singleton SHAP TreeExplainer for the recommendation Random Forest.

SHAP (SHapley Additive exPlanations) attributes a single prediction to its
input features such that ``base_value + Σ contributions == prediction`` exactly
(local accuracy). For tree ensembles, :class:`shap.TreeExplainer` computes these
Shapley values in polynomial time via the TreeSHAP algorithm — no sampling, no
GPU, fully deterministic.

Design constraints honored here
-------------------------------
* **Built once.** The explainer is constructed lazily on first use and cached,
  keyed by the model object's identity. A hot model swap
  (:func:`app.ml.inference.model_loader.reload_modelo` rebinds to a new object)
  is detected automatically and triggers a one-time rebuild — never per request.
* **Optional dependency.** ``shap`` is imported guardedly. If it is not
  installed, :func:`is_available` returns ``False`` and :func:`explain` returns
  ``None``; the XAI endpoints then degrade gracefully (global importance + a
  reasoning fallback) and the recommendation pipeline is wholly unaffected.
* **Never raises into a request.** Any explainer failure is logged and converted
  to ``None``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

log = logging.getLogger(__name__)

try:  # Optional dependency — see [project.optional-dependencies].xai in pyproject.
    import shap

    _SHAP_IMPORT_ERROR: str | None = None
except Exception as exc:  # pragma: no cover - exercised only without shap installed
    shap = None
    _SHAP_IMPORT_ERROR = str(exc)


@dataclass(frozen=True)
class ShapContribution:
    """Signed SHAP impact of one feature on the predicted next-week price.

    ``impact < 0`` lowers the predicted price (good news for "wait"); ``impact >
    0`` raises it. Magnitude is in the target's units (€/L).
    """

    feature: str
    impact: float


@dataclass(frozen=True)
class ShapExplanation:
    """Local additive explanation for a single prediction."""

    base_value: float
    prediction: float
    contributions: list[ShapContribution]


_lock = threading.Lock()
_explainer: Any | None = None
_explainer_model_id: int | None = None


def is_available() -> bool:
    """True when the ``shap`` library is importable."""
    return shap is not None


def import_error() -> str | None:
    """The import error message when shap is unavailable, else None."""
    return _SHAP_IMPORT_ERROR


def _get_explainer(model: Any) -> Any | None:
    """Return a TreeExplainer for ``model``, building/rebuilding as needed.

    Cached by ``id(model)``; a different model object (hot reload) rebuilds.
    Returns None if shap is missing or construction fails.
    """
    global _explainer, _explainer_model_id
    if shap is None:
        return None

    model_id = id(model)
    if _explainer is not None and _explainer_model_id == model_id:
        return _explainer

    with _lock:
        if _explainer is not None and _explainer_model_id == model_id:
            return _explainer
        try:
            explainer = shap.TreeExplainer(model)
        except Exception:
            log.exception("Failed to build SHAP TreeExplainer — explanations disabled")
            return None
        _explainer = explainer
        _explainer_model_id = model_id
        log.info("SHAP TreeExplainer initialised (model id=%s)", model_id)
        return explainer


def warm(model: Any) -> bool:
    """Eagerly build the explainer at startup. Best-effort; returns success.

    Called from the FastAPI lifespan so the first user request does not pay the
    (one-time, ~40 ms) construction cost. Safe to skip — :func:`explain` builds
    lazily otherwise.
    """
    return _get_explainer(model) is not None


def _base_value(raw: Any) -> float:
    """Coerce TreeExplainer.expected_value (scalar or 1-elem array) to float."""
    arr = np.ravel(np.asarray(raw, dtype=float))
    return float(arr[0]) if arr.size else 0.0


def _contributions(raw: Any, names: list[str]) -> list[ShapContribution]:
    """Map a (1, n_features) SHAP value row onto feature names, sorted by |impact|."""
    values = np.asarray(raw, dtype=float)
    if values.ndim == 2:
        values = values[0]
    values = np.ravel(values)
    pairs = [
        ShapContribution(feature=name, impact=round(float(v), 5))
        for name, v in zip(names, values, strict=False)
    ]
    pairs.sort(key=lambda c: abs(c.impact), reverse=True)
    return pairs


def explain(
    model: Any, features: NDArray[np.float64], names: list[str]
) -> ShapExplanation | None:
    """Explain a single prediction. Returns None on any failure (never raises).

    ``features`` must be the exact (1, n) inference vector the model consumes
    (same preprocessing / column order as training), and ``names`` the matching
    human-readable raw feature names in that order.
    """
    explainer = _get_explainer(model)
    if explainer is None:
        return None
    try:
        shap_values = explainer.shap_values(features)
        base = _base_value(explainer.expected_value)
        contributions = _contributions(shap_values, names)
    except Exception:
        log.exception("SHAP explanation failed — returning None (graceful degradation)")
        return None

    prediction = base + sum(c.impact for c in contributions)
    return ShapExplanation(
        base_value=round(base, 5),
        prediction=round(prediction, 5),
        contributions=contributions,
    )


def reset() -> None:
    """Drop the cached explainer (used by tests and on model reload)."""
    global _explainer, _explainer_model_id
    with _lock:
        _explainer = None
        _explainer_model_id = None
