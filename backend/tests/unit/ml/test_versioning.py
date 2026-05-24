"""Unit tests for app.ml.lifecycle.versioning — pure filesystem, no ML deps.

Model files are written as opaque bytes: ``ArtifactStore`` never loads them,
so these tests stay fast and deterministic without training a real forest.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.ml.lifecycle.exceptions import InvalidArtifactError, VersionNotFoundError
from app.ml.lifecycle.versioning import (
    ArtifactStore,
    build_metadata,
    build_metrics,
    default_artifacts_root,
    new_version_id,
)

_ARTIFACT = {
    "trained_at": "2026-05-24T03:00:00+00:00",
    "sklearn_version": "1.5.0",
    "features_names": ["distancia", "mes"],
    "hyperparameters": {"n_estimators": 300},
    "split_strategy": "time_based",
    "split_quantile": 0.8,
    "split_date": "2026-05-01",
    "n_train_rows": 800,
    "n_test_rows": 200,
    "mae": 0.012,
    "rmse": 0.018,
    "r2": 0.91,
    "r2_oob": 0.88,
}


def _seed_version(store: ArtifactStore, version: str, *, body: bytes = b"model") -> None:
    store.prepare_version_dir(version)
    store.version_model_path(version).write_bytes(body)
    store.write_sidecars(
        version,
        build_metadata(_ARTIFACT, version, dataset_rows=1000),
        build_metrics(_ARTIFACT),
    )


# ── version ids ─────────────────────────────────────────────────────────────


def test_new_version_id_is_colon_free_and_sortable() -> None:
    older = new_version_id(datetime(2026, 5, 24, 3, 0, 0, tzinfo=UTC))
    newer = new_version_id(datetime(2026, 5, 31, 3, 0, 0, tzinfo=UTC))
    assert ":" not in older
    assert older == "2026-05-24T03-00-00"
    assert older < newer  # lexical order == chronological order


def test_default_artifacts_root_points_to_backend_artifacts() -> None:
    root = default_artifacts_root()
    assert root.name == "artifacts"
    assert root.parent.name == "backend"


# ── metadata / metrics builders ───────────────────────────────────────────────


def test_build_metrics_extracts_all_four() -> None:
    metrics = build_metrics(_ARTIFACT)
    assert metrics == {"mae": 0.012, "rmse": 0.018, "r2": 0.91, "r2_oob": 0.88}


def test_build_metrics_coerces_non_finite_to_none() -> None:
    metrics = build_metrics({"mae": float("nan"), "rmse": float("inf"), "r2": None})
    assert metrics == {"mae": None, "rmse": None, "r2": None, "r2_oob": None}


def test_build_metadata_carries_reproducibility_fields() -> None:
    meta = build_metadata(_ARTIFACT, "v1", dataset_rows=1000, app_version="0.1.0", git_sha="abc123")
    assert meta["version"] == "v1"
    assert meta["dataset_rows"] == 1000
    assert meta["app_version"] == "0.1.0"
    assert meta["git_sha"] == "abc123"
    assert meta["feature_names"] == ["distancia", "mes"]
    assert meta["hyperparameters"] == {"n_estimators": 300}
    assert meta["split_strategy"] == "time_based"


# ── write + read round-trip ────────────────────────────────────────────────────


def test_write_and_read_sidecars_round_trip(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-24T03-00-00")
    assert store.read_metrics("2026-05-24T03-00-00")["mae"] == 0.012
    assert store.read_metadata("2026-05-24T03-00-00")["version"] == "2026-05-24T03-00-00"


def test_sidecar_json_is_strict_and_sorted(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "v1")
    raw = (store.version_dir("v1") / "metrics.json").read_text(encoding="utf-8")
    assert "NaN" not in raw  # strict JSON, no non-finite tokens
    assert raw.index('"mae"') < raw.index('"r2"')  # sort_keys ordering


def test_list_versions_sorted_and_only_with_model(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-31T03-00-00")
    _seed_version(store, "2026-05-24T03-00-00")
    # A stray dir without model.pkl must be ignored.
    (store.archived_dir / "garbage").mkdir(parents=True)
    assert store.list_versions() == ["2026-05-24T03-00-00", "2026-05-31T03-00-00"]
    assert store.latest_version() == "2026-05-31T03-00-00"


def test_list_versions_empty_when_no_archive(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    assert store.list_versions() == []
    assert store.latest_version() is None


# ── validation ─────────────────────────────────────────────────────────────────


def test_validate_version_missing(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(VersionNotFoundError):
        store.validate_version("nope")


def test_validate_version_empty_file(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.prepare_version_dir("v1")
    store.version_model_path("v1").write_bytes(b"")
    with pytest.raises(InvalidArtifactError):
        store.validate_version("v1")


# ── activation ───────────────────────────────────────────────────────────────


def test_activate_copies_model_and_sidecars(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-24T03-00-00", body=b"FOREST")
    store.activate("2026-05-24T03-00-00")

    assert store.active_model_path.read_bytes() == b"FOREST"
    assert store.active_version() == "2026-05-24T03-00-00"
    assert store.read_active_metrics() == {
        "mae": 0.012,
        "rmse": 0.018,
        "r2": 0.91,
        "r2_oob": 0.88,
    }
    assert store.resolve_loadable_path() == store.active_model_path


def test_activate_is_atomic_overwrite(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-24T03-00-00", body=b"OLD")
    store.activate("2026-05-24T03-00-00")
    _seed_version(store, "2026-05-31T03-00-00", body=b"NEW")
    store.activate("2026-05-31T03-00-00")

    assert store.active_model_path.read_bytes() == b"NEW"
    assert store.active_version() == "2026-05-31T03-00-00"
    # No leftover temp files from the atomic swap.
    assert not list(store.active_dir.glob(".tmp_*"))


def test_activate_missing_version_raises(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(VersionNotFoundError):
        store.activate("ghost")


# ── loadable-path resolution / legacy fallback ─────────────────────────────────


def test_resolve_loadable_path_prefers_active_over_legacy(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.legacy_model_path.write_bytes(b"legacy")
    assert store.resolve_loadable_path() == store.legacy_model_path  # only legacy yet
    _seed_version(store, "v1")
    store.activate("v1")
    assert store.resolve_loadable_path() == store.active_model_path  # active wins


def test_resolve_loadable_path_none_when_empty(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    assert store.resolve_loadable_path() is None
