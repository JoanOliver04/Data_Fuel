"""Unit tests for ML observability metrics."""

from datetime import UTC, datetime
from pathlib import Path

from app.core.metrics import REGISTRY
from app.ml.inference import model_loader
from app.ml.lifecycle.history import TrainingRunStatus
from app.ml.lifecycle.pipeline import RetrainPipeline


def test_publish_model_metrics_sets_gauges_and_info() -> None:
    model_loader._publish_model_metrics(
        {"version": "vTEST", "trained_at": "2026-01-01", "mae": 0.5, "r2": 0.9}
    )
    assert REGISTRY.get_sample_value("datafuel_ml_model_loaded") == 1.0
    assert REGISTRY.get_sample_value("datafuel_ml_model_mae") == 0.5
    assert REGISTRY.get_sample_value("datafuel_ml_model_r2") == 0.9
    assert (
        REGISTRY.get_sample_value(
            "datafuel_ml_model_info", {"version": "vTEST", "trained_at": "2026-01-01"}
        )
        == 1.0
    )


def test_reload_failure_increments_counter(tmp_path: Path) -> None:
    before = (
        REGISTRY.get_sample_value("datafuel_ml_model_reloads_total", {"result": "failure"})
        or 0.0
    )
    assert model_loader.reload_modelo(tmp_path / "missing.pkl") is False
    after = (
        REGISTRY.get_sample_value("datafuel_ml_model_reloads_total", {"result": "failure"})
        or 0.0
    )
    assert after == before + 1.0


def test_outcome_records_retrain_total_and_duration() -> None:
    pipeline = RetrainPipeline()
    status_before = (
        REGISTRY.get_sample_value("datafuel_ml_retrain_total", {"status": "rejected"}) or 0.0
    )
    dur_before = (
        REGISTRY.get_sample_value("datafuel_ml_retrain_duration_seconds_count") or 0.0
    )

    pipeline._outcome(TrainingRunStatus.REJECTED, "v1", "some reason", None, datetime.now(UTC))

    assert (
        REGISTRY.get_sample_value("datafuel_ml_retrain_total", {"status": "rejected"}) or 0.0
    ) == status_before + 1.0
    assert (
        REGISTRY.get_sample_value("datafuel_ml_retrain_duration_seconds_count") or 0.0
    ) == dur_before + 1.0
