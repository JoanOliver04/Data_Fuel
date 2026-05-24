"""Versioned artifact storage with atomic, symlink-free activation.

Layout under the artifacts root (default ``backend/artifacts``)::

    artifacts/
        modelo_combustible.pkl          # legacy single-file model (kept)
        active/
            model.pkl                   # the live model the API loads
            metadata.json
            metrics.json
        archived/
            2026-05-24T03-00-00/
                model.pkl
                metadata.json
                metrics.json

Activation never uses symlinks: a directory symlink would require Developer
Mode / admin on Windows and can fail silently. Instead each file is swapped
into ``active/`` with :func:`os.replace`, which is atomic on POSIX and on NTFS
when source and destination share a volume — so a concurrent reader sees
either the whole old file or the whole new one, never a partial write.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ml.lifecycle.exceptions import InvalidArtifactError, VersionNotFoundError

_MODEL_FILE = "model.pkl"
_METADATA_FILE = "metadata.json"
_METRICS_FILE = "metrics.json"
_LEGACY_MODEL_FILE = "modelo_combustible.pkl"
_VERSION_FMT = "%Y-%m-%dT%H-%M-%S"  # colon-free: valid as a directory name on Windows


def default_artifacts_root() -> Path:
    """Return ``backend/artifacts`` derived from this module's location.

    No hardcoded absolute paths: callers may override the root (tests pass a
    ``tmp_path``), but the default mirrors the legacy ``model_loader`` layout.
    """
    # versioning.py → lifecycle → ml → app → backend
    return Path(__file__).resolve().parents[3] / "artifacts"


def new_version_id(now: datetime | None = None) -> str:
    """Return a sortable, filesystem-safe version id (UTC, second precision)."""
    moment = now or datetime.now(UTC)
    return moment.astimezone(UTC).strftime(_VERSION_FMT)


def _finite_or_none(value: Any) -> float | None:
    """Coerce a metric to ``float`` or ``None`` when missing / non-finite.

    JSON has no NaN/Inf; persisting ``None`` keeps the sidecar strictly valid
    and round-trippable by any standards-compliant reader.
    """
    if value is None:
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def build_metrics(artifact: Mapping[str, Any]) -> dict[str, float | None]:
    """Extract the evaluation metrics from a trained-artifact dict."""
    return {
        "mae": _finite_or_none(artifact.get("mae")),
        "rmse": _finite_or_none(artifact.get("rmse")),
        "r2": _finite_or_none(artifact.get("r2")),
        "r2_oob": _finite_or_none(artifact.get("r2_oob")),
    }


def build_metadata(
    artifact: Mapping[str, Any],
    version: str,
    *,
    dataset_rows: int,
    app_version: str | None = None,
    git_sha: str | None = None,
) -> dict[str, Any]:
    """Assemble the reproducibility metadata for a trained-artifact dict."""
    return {
        "version": version,
        "trained_at": artifact.get("trained_at"),
        "sklearn_version": artifact.get("sklearn_version"),
        "feature_names": list(artifact.get("features_names", [])),
        "hyperparameters": dict(artifact.get("hyperparameters", {})),
        "split_strategy": artifact.get("split_strategy"),
        "split_quantile": artifact.get("split_quantile"),
        "split_date": artifact.get("split_date"),
        "n_train_rows": artifact.get("n_train_rows"),
        "n_test_rows": artifact.get("n_test_rows"),
        "dataset_rows": dataset_rows,
        "app_version": app_version,
        "git_sha": git_sha,
    }


def _atomic_replace_via(dst: Path, write: Any) -> None:
    """Run ``write(tmp_path)`` then atomically move the temp file onto ``dst``."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dst.parent, prefix=".tmp_", suffix=dst.suffix)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write(tmp)
        os.replace(tmp, dst)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _atomic_copy(src: Path, dst: Path) -> None:
    """Copy ``src`` onto ``dst`` atomically (stream via a sibling temp file)."""
    _atomic_replace_via(dst, lambda tmp: shutil.copyfile(src, tmp))


def _atomic_write_json(dst: Path, payload: Mapping[str, Any]) -> None:
    """Serialise ``payload`` to ``dst`` atomically with stable key ordering."""

    def _write(tmp: Path) -> None:
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    _atomic_replace_via(dst, _write)


class ArtifactStore:
    """Filesystem store for versioned model artifacts. Pure I/O, no ML deps."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_artifacts_root()).resolve()

    # ── Paths ───────────────────────────────────────────────────────────────
    @property
    def active_dir(self) -> Path:
        return self.root / "active"

    @property
    def archived_dir(self) -> Path:
        return self.root / "archived"

    @property
    def active_model_path(self) -> Path:
        return self.active_dir / _MODEL_FILE

    @property
    def legacy_model_path(self) -> Path:
        return self.root / _LEGACY_MODEL_FILE

    def version_dir(self, version: str) -> Path:
        return self.archived_dir / version

    def version_model_path(self, version: str) -> Path:
        return self.version_dir(version) / _MODEL_FILE

    # ── Write paths ─────────────────────────────────────────────────────────
    def prepare_version_dir(self, version: str) -> Path:
        """Create (if needed) and return ``archived/<version>``.

        The trainer writes ``model.pkl`` directly here; sidecars are written
        afterwards via :meth:`write_sidecars`.
        """
        path = self.version_dir(version)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_sidecars(
        self,
        version: str,
        metadata: Mapping[str, Any],
        metrics: Mapping[str, Any],
    ) -> None:
        """Persist ``metadata.json`` and ``metrics.json`` next to the model."""
        version_dir = self.version_dir(version)
        version_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(version_dir / _METADATA_FILE, metadata)
        _atomic_write_json(version_dir / _METRICS_FILE, metrics)

    # ── Read paths ──────────────────────────────────────────────────────────
    def list_versions(self) -> list[str]:
        """Return archived version ids that hold a model, sorted oldest→newest.

        Version ids are UTC timestamps, so lexical order equals chronological
        order.
        """
        if not self.archived_dir.exists():
            return []
        return sorted(
            entry.name
            for entry in self.archived_dir.iterdir()
            if entry.is_dir() and (entry / _MODEL_FILE).is_file()
        )

    def latest_version(self) -> str | None:
        versions = self.list_versions()
        return versions[-1] if versions else None

    def read_metadata(self, version: str) -> dict[str, Any]:
        return self._read_json(self.version_dir(version) / _METADATA_FILE)

    def read_metrics(self, version: str) -> dict[str, Any]:
        return self._read_json(self.version_dir(version) / _METRICS_FILE)

    def read_active_metadata(self) -> dict[str, Any] | None:
        path = self.active_dir / _METADATA_FILE
        return self._read_json(path) if path.is_file() else None

    def read_active_metrics(self) -> dict[str, Any] | None:
        path = self.active_dir / _METRICS_FILE
        return self._read_json(path) if path.is_file() else None

    def active_version(self) -> str | None:
        metadata = self.read_active_metadata()
        version = metadata.get("version") if metadata else None
        return str(version) if version is not None else None

    def resolve_loadable_path(self) -> Path | None:
        """Path the API should load: active model first, else the legacy file."""
        if self.active_model_path.is_file():
            return self.active_model_path
        if self.legacy_model_path.is_file():
            return self.legacy_model_path
        return None

    # ── Activation ──────────────────────────────────────────────────────────
    def validate_version(self, version: str) -> None:
        """Raise if the version's model file is missing or empty."""
        model_path = self.version_model_path(version)
        if not model_path.is_file():
            raise VersionNotFoundError(f"No model for version {version!r} at {model_path}")
        if model_path.stat().st_size == 0:
            raise InvalidArtifactError(f"Model for version {version!r} is empty: {model_path}")

    def activate(self, version: str) -> None:
        """Atomically promote ``archived/<version>`` to ``active/``.

        The model file is swapped first via :func:`os.replace`; an interrupted
        activation therefore leaves the previously active model fully intact.
        """
        self.validate_version(version)
        src_dir = self.version_dir(version)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        _atomic_copy(src_dir / _MODEL_FILE, self.active_model_path)
        for sidecar in (_METADATA_FILE, _METRICS_FILE):
            src = src_dir / sidecar
            if src.is_file():
                _atomic_copy(src, self.active_dir / sidecar)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
