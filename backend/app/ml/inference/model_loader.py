"""In-memory holder for the Random Forest recommendation artifact.

Call :func:`load_modelo` once at FastAPI startup (lifespan). Endpoints call
:func:`get_modelo` to retrieve the artifact dict; it returns ``None`` if not
loaded, in which case the endpoint must respond with 503.

The artifact path is resolved through :class:`ArtifactStore`, so the live
``artifacts/active/model.pkl`` is preferred and the legacy single-file
``artifacts/modelo_combustible.pkl`` is used as a fallback.

Hot reload (:func:`reload_modelo`) lets the retraining pipeline swap the model
without restarting the API. The swap is a single atomic rebind of the module
global: ``get_modelo`` never takes a lock, so in-flight requests keep using
whatever artifact dict they already fetched (model + label encoders travel
together in one dict, so they can never be mismatched mid-request). A lock only
serialises concurrent *reloaders* and is held across the slow ``joblib.load``,
during which the previous model stays live.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import joblib

from app.ml.lifecycle.exceptions import InvalidArtifactError
from app.ml.lifecycle.versioning import ArtifactStore

log = logging.getLogger(__name__)

_lock = threading.Lock()
_modelo: dict[str, Any] | None = None


def _resolve_path(path: Path | None) -> Path | None:
    """Return the explicit path, or the store's active→legacy resolution."""
    if path is not None:
        return path
    return ArtifactStore().resolve_loadable_path()


def _read_artifact(path: Path) -> dict[str, Any]:
    """Load and structurally validate an artifact dict from disk."""
    artifact: Any = joblib.load(path)
    if not isinstance(artifact, dict) or "model" not in artifact:
        raise InvalidArtifactError(
            f"Artifact at {path} is not a valid model bundle (missing 'model')"
        )
    return artifact


def _log_loaded(path: Path, artifact: dict[str, Any], *, action: str) -> None:
    log.info(
        "ML model %s from %s (trained_at=%s, mae=%.4f, r2=%.4f)",
        action,
        path,
        artifact.get("trained_at"),
        artifact.get("mae", float("nan")),
        artifact.get("r2", float("nan")),
    )


def load_modelo(path: Path | None = None) -> None:
    """Load the artifact into memory at startup. Resilient and idempotent.

    A missing or unreadable artifact leaves the model unset (``get_modelo``
    returns ``None`` → endpoints answer 503) rather than crashing startup.
    """
    global _modelo
    resolved = _resolve_path(path)
    if resolved is None or not resolved.exists():
        log.warning(
            "ML model not found (resolved=%s) — /predictions/recommendation will 503",
            resolved,
        )
        return
    try:
        with _lock:
            artifact = _read_artifact(resolved)
            _modelo = artifact
    except Exception:
        log.exception("Failed to load ML model from %s — leaving model unset", resolved)
        return
    _log_loaded(resolved, artifact, action="loaded")


def reload_modelo(path: Path | None = None) -> bool:
    """Hot-swap the in-memory model. Returns True on success.

    On any failure the currently loaded model is preserved untouched and the
    function returns False — there is no downtime and no fallback to a broken
    artifact.
    """
    global _modelo
    resolved = _resolve_path(path)
    if resolved is None or not resolved.exists():
        log.error("Reload skipped: no artifact resolved (%s) — keeping current model", resolved)
        return False
    try:
        with _lock:
            artifact = _read_artifact(resolved)
            _modelo = artifact
    except Exception:
        log.exception("Reload failed for %s — keeping current model", resolved)
        return False
    _log_loaded(resolved, artifact, action="hot-reloaded")
    return True


def get_modelo() -> dict[str, Any] | None:
    """Return the loaded artifact dict, or None if not yet loaded."""
    return _modelo
