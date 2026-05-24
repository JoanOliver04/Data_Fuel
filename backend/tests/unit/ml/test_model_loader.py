"""Unit tests for app.ml.inference.model_loader — load, resolve, hot-reload.

Artifacts are minimal picklable dicts: the loader only checks the bundle is a
dict containing a ``model`` key, so no real estimator is needed.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import joblib
import pytest

from app.ml.inference import model_loader
from app.ml.lifecycle.versioning import ArtifactStore


@pytest.fixture(autouse=True)
def _reset_model() -> Generator[None, None, None]:
    model_loader._modelo = None
    yield
    model_loader._modelo = None


def _dump(path: Path, tag: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    artifact: dict[str, Any] = {
        "model": tag,
        "trained_at": "2026-05-24T03:00:00+00:00",
        "mae": 0.01,
        "r2": 0.9,
    }
    joblib.dump(artifact, path)
    return path


# ── load_modelo ────────────────────────────────────────────────────────────────


def test_load_modelo_missing_leaves_none(tmp_path: Path) -> None:
    model_loader.load_modelo(tmp_path / "nope.pkl")
    assert model_loader.get_modelo() is None


def test_load_modelo_from_explicit_path(tmp_path: Path) -> None:
    path = _dump(tmp_path / "model.pkl", "v1")
    model_loader.load_modelo(path)
    loaded = model_loader.get_modelo()
    assert loaded is not None
    assert loaded["model"] == "v1"


def test_load_modelo_invalid_bundle_leaves_none(tmp_path: Path) -> None:
    path = tmp_path / "bad.pkl"
    joblib.dump(["not", "a", "dict"], path)
    model_loader.load_modelo(path)
    assert model_loader.get_modelo() is None


# ── reload_modelo ────────────────────────────────────────────────────────────


def test_reload_swaps_model(tmp_path: Path) -> None:
    model_loader.load_modelo(_dump(tmp_path / "v1.pkl", "v1"))
    assert model_loader.reload_modelo(_dump(tmp_path / "v2.pkl", "v2")) is True
    loaded = model_loader.get_modelo()
    assert loaded is not None and loaded["model"] == "v2"


def test_reload_failure_keeps_current_model(tmp_path: Path) -> None:
    model_loader.load_modelo(_dump(tmp_path / "good.pkl", "good"))
    corrupt = tmp_path / "corrupt.pkl"
    corrupt.write_bytes(b"\x00\x01 not a pickle")
    assert model_loader.reload_modelo(corrupt) is False
    loaded = model_loader.get_modelo()
    assert loaded is not None and loaded["model"] == "good"


def test_reload_missing_path_keeps_current_model(tmp_path: Path) -> None:
    model_loader.load_modelo(_dump(tmp_path / "good.pkl", "good"))
    assert model_loader.reload_modelo(tmp_path / "ghost.pkl") is False
    loaded = model_loader.get_modelo()
    assert loaded is not None and loaded["model"] == "good"


def test_reload_invalid_bundle_keeps_current_model(tmp_path: Path) -> None:
    model_loader.load_modelo(_dump(tmp_path / "good.pkl", "good"))
    bad = tmp_path / "bad.pkl"
    joblib.dump({"no_model_key": True}, bad)
    assert model_loader.reload_modelo(bad) is False
    loaded = model_loader.get_modelo()
    assert loaded is not None and loaded["model"] == "good"


# ── store-based resolution (active over legacy) ────────────────────────────────


def test_reload_resolves_active_via_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = ArtifactStore(tmp_path)
    # Seed an active model and point the loader's default store at tmp_path.
    _dump(store.active_model_path, "active-v9")
    monkeypatch.setattr(model_loader, "ArtifactStore", lambda: store)

    assert model_loader.reload_modelo() is True  # no explicit path → uses store
    loaded = model_loader.get_modelo()
    assert loaded is not None and loaded["model"] == "active-v9"


def test_reload_falls_back_to_legacy_when_no_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    _dump(store.legacy_model_path, "legacy")
    monkeypatch.setattr(model_loader, "ArtifactStore", lambda: store)

    assert model_loader.reload_modelo() is True
    loaded = model_loader.get_modelo()
    assert loaded is not None and loaded["model"] == "legacy"
