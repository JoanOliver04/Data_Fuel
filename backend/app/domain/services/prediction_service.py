"""Domain service: 48h fuel price prediction via Ridge regression."""

from __future__ import annotations

import dataclasses
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.domain.entities.fuel_type import FuelType

logger = logging.getLogger(__name__)

MIN_SAMPLES: int = 30
_CACHE_TTL_SECONDS: int = 6 * 3600
HORIZON_HOURS: int = 48
_ADVICE_THRESHOLD_PCT: float = 0.5


@dataclass(frozen=True, slots=True)
class TrainingRow:
    """Single observation for model training."""

    price: float
    recorded_at: datetime
    brand: str
    province: str


@dataclass(frozen=True, slots=True)
class PredictionResult:
    """Output of a single station price prediction."""

    current_price: float
    predicted_price: float
    change_pct: float
    advice: str
    horizon_hours: int
    model_r2: float


class PredictionService:
    """Trains and caches per-fuel-type Ridge models; predicts 48h-ahead price."""

    def __init__(self) -> None:
        # fuel_type → (pipeline, r2_score, trained_at)
        self._cache: dict[FuelType, tuple[Pipeline, float, datetime]] = {}

    def predict(
        self,
        rows: list[TrainingRow],
        current_price: float,
        brand: str,
        province: str,
        fuel_type: FuelType,
    ) -> PredictionResult | None:
        """Return a PredictionResult, or None when training data is insufficient."""
        trained = self._fresh_cached(fuel_type)
        if trained is None:
            # No usable cached model: a (re)train is required, which needs rows.
            if len(rows) < MIN_SAMPLES:
                return None
            trained = self._train_and_cache(fuel_type, rows)
        model, r2 = trained

        future = datetime.now(UTC) + timedelta(hours=HORIZON_HOURS)
        X_pred = pd.DataFrame([{
            "hour": future.hour,
            "day_of_week": future.weekday(),
            "brand": brand,
            "province": province,
        }])
        predicted = max(0.0, float(model.predict(X_pred)[0]))
        change_pct = round((predicted - current_price) / current_price * 100, 2)

        return PredictionResult(
            current_price=current_price,
            predicted_price=round(predicted, 3),
            change_pct=change_pct,
            advice=_make_advice(change_pct),
            horizon_hours=HORIZON_HOURS,
            model_r2=round(r2, 3),
        )

    def has_fresh_model(self, fuel_type: FuelType) -> bool:
        """Whether a non-stale model is cached.

        Lets callers skip the expensive training-data load entirely on a warm
        cache: ``predict`` does not touch ``rows`` when a fresh model exists.
        """
        return self._fresh_cached(fuel_type) is not None

    def _fresh_cached(self, fuel_type: FuelType) -> tuple[Pipeline, float] | None:
        cached = self._cache.get(fuel_type)
        if cached is None:
            return None
        model, r2, trained_at = cached
        if (datetime.now(UTC) - trained_at).total_seconds() < _CACHE_TTL_SECONDS:
            return model, r2
        return None

    def _train_and_cache(
        self, fuel_type: FuelType, rows: list[TrainingRow]
    ) -> tuple[Pipeline, float]:
        model, r2 = _train(rows)
        self._cache[fuel_type] = (model, r2, datetime.now(UTC))
        return model, r2

    def invalidate(self, fuel_type: FuelType | None = None) -> None:
        """Evict cached model(s). Pass None to clear all."""
        if fuel_type is None:
            self._cache.clear()
        else:
            self._cache.pop(fuel_type, None)


def _train(rows: list[TrainingRow]) -> tuple[Pipeline, float]:
    df = pd.DataFrame([
        {
            "hour": r.recorded_at.hour,
            "day_of_week": r.recorded_at.weekday(),
            "brand": r.brand,
            "province": r.province,
            "price": float(r.price),
        }
        for r in rows
    ])

    X = df[["hour", "day_of_week", "brand", "province"]]
    y = df["price"]

    # brand/province are high-cardinality free-text (thousands of distinct brands
    # nationwide), so a *dense* one-hot explodes to (n_rows, ~3300) float64 — e.g.
    # 80k rows ≈ 2 GiB. Keeping the encoder sparse (and float32) means the design
    # matrix never materializes dense: Ridge consumes it sparse, StandardScaler
    # only touches the 2 numeric columns, and ColumnTransformer's default
    # sparse_threshold (0.3) preserves the sparse stack rather than coercing it.
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), ["hour", "day_of_week"]),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=True, dtype=np.float32),
            ["brand", "province"],
        ),
    ])
    pipeline = Pipeline([("prep", preprocessor), ("reg", Ridge(alpha=1.0))])

    # Report an honest generalization estimate (k-fold CV R² on held-out folds),
    # not pipeline.score(X, y), which is the in-sample fit and overstates the
    # confidence shown to users. The returned model is still fit on all rows;
    # cross_val_score clones internally and does not fit `pipeline` itself.
    n_splits = min(5, len(df))
    started = time.perf_counter()
    r2 = (
        float(cross_val_score(pipeline, X, y, cv=n_splits, scoring="r2").mean())
        if n_splits >= 2
        else 0.0
    )

    pipeline.fit(X, y)
    elapsed = time.perf_counter() - started

    design = pipeline.named_steps["prep"].transform(X)
    logger.info(
        "48h Ridge trained — rows=%d cv_folds=%d %s fit+cv=%.2fs",
        len(df),
        n_splits,
        _describe_design_matrix(design),
        elapsed,
    )
    return pipeline, r2


def _describe_design_matrix(matrix: Any) -> str:
    """One-line description of the transformed design matrix, for logging.

    Reports sparse-vs-dense, shape, dtype and an estimated footprint next to the
    dense-equivalent it avoids — the guardrail proving the OneHotEncoder output
    stays sparse instead of allocating the ~2 GiB dense block it used to.
    Duck-types the sparse check (``nnz``) so no ``scipy`` import is needed.
    """
    n_rows, n_cols = matrix.shape
    itemsize = int(matrix.dtype.itemsize)
    dense_mb = n_rows * n_cols * itemsize / 1e6
    if hasattr(matrix, "nnz"):  # scipy sparse matrix
        nnz = int(matrix.nnz)
        # CSR-style footprint: values + 4-byte column index per nonzero, plus the
        # row-pointer array (4 bytes per row + 1).
        actual_mb = (nnz * itemsize + nnz * 4 + (n_rows + 1) * 4) / 1e6
        return (
            f"design=sparse shape=({n_rows}, {n_cols}) dtype={matrix.dtype} "
            f"nnz={nnz} ~{actual_mb:.1f}MB (dense would be ~{dense_mb:.0f}MB)"
        )
    return f"design=dense shape=({n_rows}, {n_cols}) dtype={matrix.dtype} ~{dense_mb:.1f}MB"


def _make_advice(change_pct: float) -> str:
    if change_pct <= -_ADVICE_THRESHOLD_PCT:
        return f"Espera, el precio bajará un {abs(change_pct):.1f}% en 48h"
    if change_pct >= _ADVICE_THRESHOLD_PCT:
        return f"Reposta ahora, el precio subirá un {change_pct:.1f}% en 48h"
    return "Precio estable, indistinto cuándo repostes"


def prediction_result_as_dict(result: PredictionResult) -> dict[str, Any]:
    return dataclasses.asdict(result)
