"""Singleton loader for modelo_combustible.pkl.

Call ``load_modelo()`` once at FastAPI startup (lifespan). Endpoints call
``get_modelo()`` to retrieve the artifact dict; returns None if not loaded,
in which case the endpoint must respond with 503.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib

log = logging.getLogger(__name__)

_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[3] / "artifacts" / "modelo_combustible.pkl"
)

_modelo: dict[str, Any] | None = None


def load_modelo(path: Path | None = None) -> None:
    """Load artifact into memory. Idempotent; logs warning if file absent."""
    global _modelo
    p = path or _ARTIFACT_PATH
    if not p.exists():
        log.warning(
            "ML model not found at %s — /predictions/recommendation will return 503", p
        )
        return
    _modelo = joblib.load(p)
    log.info(
        "ML model loaded from %s (trained_at=%s, mae=%.4f, r2=%.4f)",
        p,
        _modelo.get("trained_at"),
        _modelo.get("mae", float("nan")),
        _modelo.get("r2", float("nan")),
    )


def get_modelo() -> dict[str, Any] | None:
    """Return the loaded artifact dict, or None if not yet loaded."""
    return _modelo
