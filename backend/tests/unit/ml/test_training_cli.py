"""Unit tests for the retraining CLI entrypoints (exit codes, no DB)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pytest

from app.ml.lifecycle.history import TrainingRunStatus
from app.ml.lifecycle.pipeline import RetrainOutcome
from app.ml.lifecycle.versioning import ArtifactStore, build_metrics
from app.ml.training import activate as activate_cli
from app.ml.training import evaluate as evaluate_cli
from app.ml.training import retrain as retrain_cli

_ARTIFACT = {"mae": 0.04, "rmse": 0.05, "r2": 0.9, "r2_oob": 0.88}


def _seed_version(store: ArtifactStore, version: str, *, mae: float, r2: float) -> None:
    store.prepare_version_dir(version)
    joblib.dump({"model": "x"}, store.version_model_path(version))
    store.write_sidecars(
        version,
        {"version": version},
        build_metrics({"mae": mae, "rmse": 0.05, "r2": r2, "r2_oob": r2}),
    )


# ── retrain CLI: exit-code mapping ─────────────────────────────────────────────


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (TrainingRunStatus.ACTIVATED, 0),
        (TrainingRunStatus.REJECTED, 2),
        (TrainingRunStatus.FAILED, 1),
    ],
)
def test_retrain_cli_exit_codes(
    status: TrainingRunStatus, code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakePipeline:
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

        async def run(self) -> RetrainOutcome:
            return RetrainOutcome(
                status=status, version="v", reason="r", metrics=None, duration_seconds=1.0
            )

    monkeypatch.setattr(retrain_cli, "RetrainPipeline", _FakePipeline)
    assert retrain_cli.main() == code


# ── evaluate CLI ───────────────────────────────────────────────────────────────


def test_evaluate_cli_accepts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-24T03-00-00", mae=0.04, r2=0.92)
    store.activate("2026-05-24T03-00-00")
    _seed_version(store, "2026-05-31T03-00-00", mae=0.035, r2=0.93)  # better
    monkeypatch.setattr(evaluate_cli, "ArtifactStore", lambda: store)

    monkeypatch.setattr("sys.argv", ["evaluate", "--version", "2026-05-31T03-00-00"])
    assert evaluate_cli.main() == 0


def test_evaluate_cli_rejects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-24T03-00-00", mae=0.04, r2=0.92)
    store.activate("2026-05-24T03-00-00")
    _seed_version(store, "2026-05-31T03-00-00", mae=0.10, r2=0.60)  # much worse
    monkeypatch.setattr(evaluate_cli, "ArtifactStore", lambda: store)

    monkeypatch.setattr("sys.argv", ["evaluate", "--version", "2026-05-31T03-00-00"])
    assert evaluate_cli.main() == 2


def test_evaluate_cli_unknown_version_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = ArtifactStore(tmp_path)
    monkeypatch.setattr(evaluate_cli, "ArtifactStore", lambda: store)
    monkeypatch.setattr("sys.argv", ["evaluate"])  # no versions, default latest → None
    assert evaluate_cli.main() == 1


# ── activate CLI ───────────────────────────────────────────────────────────────


def test_activate_cli_unknown_version_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = ArtifactStore(tmp_path)
    monkeypatch.setattr(activate_cli, "ArtifactStore", lambda: store)
    monkeypatch.setattr("sys.argv", ["activate", "--version", "ghost"])
    assert activate_cli.main() == 1


def test_activate_cli_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    _seed_version(store, "2026-05-24T03-00-00", mae=0.04, r2=0.92)
    monkeypatch.setattr(activate_cli, "ArtifactStore", lambda: store)

    async def _noop_record(s: ArtifactStore, version: str) -> None:
        return None

    monkeypatch.setattr(activate_cli, "_record_activation", _noop_record)
    monkeypatch.setattr("sys.argv", ["activate", "--version", "2026-05-24T03-00-00"])

    assert activate_cli.main() == 0
    assert store.active_version() == "2026-05-24T03-00-00"
