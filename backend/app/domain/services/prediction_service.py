"""Domain service: 48h fuel price prediction via Ridge regression."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.domain.entities.fuel_type import FuelType

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
        if len(rows) < MIN_SAMPLES:
            return None

        model, r2 = self._get_or_train(fuel_type, rows)

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

    def _get_or_train(
        self, fuel_type: FuelType, rows: list[TrainingRow]
    ) -> tuple[Pipeline, float]:
        cached = self._cache.get(fuel_type)
        if cached is not None:
            model, r2, trained_at = cached
            if (datetime.now(UTC) - trained_at).total_seconds() < _CACHE_TTL_SECONDS:
                return model, r2

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

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), ["hour", "day_of_week"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["brand", "province"]),
    ])
    pipeline = Pipeline([("prep", preprocessor), ("reg", Ridge(alpha=1.0))])
    pipeline.fit(X, y)
    return pipeline, float(pipeline.score(X, y))


def _make_advice(change_pct: float) -> str:
    if change_pct <= -_ADVICE_THRESHOLD_PCT:
        return f"Espera, el precio bajará un {abs(change_pct):.1f}% en 48h"
    if change_pct >= _ADVICE_THRESHOLD_PCT:
        return f"Reposta ahora, el precio subirá un {change_pct:.1f}% en 48h"
    return "Precio estable, indistinto cuándo repostes"


def prediction_result_as_dict(result: PredictionResult) -> dict:  # type: ignore[return]
    return dataclasses.asdict(result)
