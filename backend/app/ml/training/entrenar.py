"""Train a Random Forest regressor on datos.csv and persist model artifacts.

Validation strategy
-------------------
This trainer uses a **time-based holdout** (rows ordered by ``fecha`` and the
top quantile reserved as test) as the primary evaluation. A random 80/20
split of the same data would inflate R² because the same station appears in
both halves on different days — the model would memorize per-station price
levels rather than forecast forward in time. The persisted ``mae`` and
``r2`` keys therefore reflect honest forecast performance on unseen future
weeks.

The trainer additionally computes the out-of-bag R² (``r2_oob``) which is a
free, independent generalization estimate produced by the bagging procedure
itself, and persists the trained hyperparameters, feature importances, and
training-set sizes for full reproducibility.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# Expected CSV layout (post-self-engineered features): 17 columns, strict order.
_COLUMNS_EXPECTED = [
    "fecha",
    "precio",
    "municipio",
    "distancia",
    "tipo_combustible",
    "comarca",
    "dia_de_la_semana",
    "es_festivo",
    "precio_semana_anterior",
    "tendencia_ultimos_30_dias",
    "is_low_cost",
    "mes",
    "precio_medio_municipio",
    "es_autopista",
    "precio_vs_media_comarca",
    "momentum_7d",
    "precio_prox_semana",
]

TARGET_COLUMN = "precio_prox_semana"

MIN_ROWS: int = 100
MAX_TRAIN_ROWS: int = 1_500_000
MAX_TEST_ROWS: int = 300_000
TIME_SPLIT_QUANTILE: float = 0.8

FEATURE_COLUMNS: list[str] = [
    "distancia",
    "tipo_combustible",
    "dia_de_la_semana",
    "es_festivo",
    "precio_semana_anterior",
    "tendencia_ultimos_30_dias",
    "is_low_cost",
    "mes",
    "precio_medio_municipio",
    "es_autopista",
    "precio_vs_media_comarca",
    "momentum_7d",
    "año",
    "municipio_enc",
    "comarca_enc",
]

# Hyperparameters tuned via a one-off search on the v1.0 17-column dataset:
# more estimators improve stability, max_depth=30 caps memory growth on the
# full-history corpus, min_samples_leaf=3 reduces leaf-level overfit, and
# max_features="sqrt" introduces per-tree feature subsampling for ensemble
# diversity. n_jobs=6 leaves headroom on standard 8-12 core dev machines.
HYPERPARAMETERS: dict[str, Any] = {
    "n_estimators": 300,
    "max_depth": 30,
    "min_samples_leaf": 3,
    "max_features": "sqrt",
    "bootstrap": True,
    "oob_score": True,
    "n_jobs": 6,
    "random_state": 42,
}


def ejecutar_entrenamiento(
    csv_path: Path,
    output_path: Path,
    min_rows: int = MIN_ROWS,
    max_rows: int = MAX_TRAIN_ROWS,
    max_test_rows: int = MAX_TEST_ROWS,
) -> dict[str, Any]:
    """Load csv_path, train Random Forest, persist artifact dict to output_path.

    Returns the artifact dict (useful for tests without loading from disk).
    """
    df = _load_and_validate(csv_path, min_rows)

    logger.info("Rows read: %d", len(df))
    df = df.dropna().copy()
    logger.info("Rows after dropna: %d", len(df))

    le_municipio: LabelEncoder = LabelEncoder()
    le_comarca: LabelEncoder = LabelEncoder()
    df["municipio_enc"] = le_municipio.fit_transform(df["municipio"])
    df["comarca_enc"] = le_comarca.fit_transform(df["comarca"])

    train_df, test_df, split_date = _time_split(df, TIME_SPLIT_QUANTILE)
    train_df, test_df = _cap_sample_sizes(train_df, test_df, max_rows, max_test_rows)

    logger.info(
        "Time split @ %s — train=%d test=%d",
        split_date.date() if hasattr(split_date, "date") else split_date,
        len(train_df),
        len(test_df),
    )

    X_train = train_df[FEATURE_COLUMNS].to_numpy()
    y_train = train_df[TARGET_COLUMN].to_numpy()
    X_test = test_df[FEATURE_COLUMNS].to_numpy()
    y_test = test_df[TARGET_COLUMN].to_numpy()

    model: RandomForestRegressor = RandomForestRegressor(**HYPERPARAMETERS)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))
    r2_oob = float(model.oob_score_)

    logger.info("MAE (time-split holdout): %.4f", mae)
    logger.info("R²  (time-split holdout): %.4f", r2)
    logger.info("R²  (out-of-bag estimate): %.4f", r2_oob)

    importances = _log_feature_importances(model)

    artifact: dict[str, Any] = {
        "model": model,
        "label_encoder_municipio": le_municipio,
        "label_encoder_comarca": le_comarca,
        "features_names": FEATURE_COLUMNS,
        "trained_at": datetime.now(UTC).isoformat(),
        "mae": mae,
        "r2": r2,
        "r2_oob": r2_oob,
        "split_strategy": "time_based",
        "split_quantile": TIME_SPLIT_QUANTILE,
        "split_date": (
            split_date.isoformat() if hasattr(split_date, "isoformat") else str(split_date)
        ),
        "n_train_rows": len(X_train),
        "n_test_rows": len(X_test),
        "hyperparameters": dict(HYPERPARAMETERS),
        "feature_importances": importances,
        "sklearn_version": sklearn.__version__,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)
    logger.info("Artifact saved: %s", output_path)

    return artifact


def _time_split(
    df: pd.DataFrame, quantile: float
) -> tuple[pd.DataFrame, pd.DataFrame, Any]:
    """Sort by ``fecha`` and split at the given quantile; tail becomes test."""
    df_sorted = df.sort_values("fecha").reset_index(drop=True)
    split_date = df_sorted["fecha"].quantile(quantile)
    train_df = df_sorted[df_sorted["fecha"] < split_date].copy()
    test_df = df_sorted[df_sorted["fecha"] >= split_date].copy()
    if len(test_df) == 0:
        # Degenerate case (e.g. very small synthetic test fixtures): fall back
        # to a random 80/20 split so the trainer still produces a model.
        from sklearn.model_selection import train_test_split

        train_df, test_df = train_test_split(
            df_sorted, test_size=0.2, random_state=42
        )
    return train_df, test_df, split_date


def _cap_sample_sizes(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    max_train: int,
    max_test: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Subsample each half independently to keep memory bounded."""
    if len(train_df) > max_train:
        train_df = train_df.sample(n=max_train, random_state=42).reset_index(drop=True)
        logger.info("Train pool subsampled to %d rows (max_train cap)", len(train_df))
    if len(test_df) > max_test:
        test_df = test_df.sample(n=max_test, random_state=42).reset_index(drop=True)
        logger.info("Test pool subsampled to %d rows (max_test cap)", len(test_df))
    return train_df, test_df


def _log_feature_importances(model: RandomForestRegressor) -> dict[str, float]:
    """Log the top-10 feature importances and return the full mapping."""
    importances = {
        feat: float(imp)
        for feat, imp in zip(FEATURE_COLUMNS, model.feature_importances_, strict=True)
    }
    top = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)[:10]
    logger.info("Feature importances (top 10):")
    for name, imp in top:
        logger.info("  %-26s  %.4f", name, imp)
    return importances


def _load_and_validate(path: Path, min_rows: int) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df: pd.DataFrame = pd.read_csv(path, parse_dates=["fecha"])
    actual_cols = list(df.columns)

    if actual_cols != _COLUMNS_EXPECTED:
        raise ValueError(
            f"Invalid columns {actual_cols}. Expected {_COLUMNS_EXPECTED}."
        )

    if len(df) < min_rows:
        raise ValueError(
            f"CSV has {len(df)} rows; minimum required is {min_rows}."
        )

    df["es_festivo"] = df["es_festivo"].astype(int)
    df["is_low_cost"] = df["is_low_cost"].astype(int)
    df["es_autopista"] = df["es_autopista"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["año"] = df["fecha"].dt.year
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _backend_root = Path(__file__).resolve().parents[3]
    _csv = _backend_root / "data" / "datos.csv"
    _out = _backend_root / "artifacts" / "modelo_combustible.pkl"

    try:
        ejecutar_entrenamiento(_csv, _out)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc
