"""Train a Random Forest regressor on datos.csv and persist model artifacts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# Expected CSV layout (post-Pizarra B): 11 columns in this strict order.
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
    "precio_prox_semana",
]

TARGET_COLUMN = "precio_prox_semana"

MIN_ROWS: int = 100

FEATURE_COLUMNS: list[str] = [
    "distancia",
    "tipo_combustible",
    "dia_de_la_semana",
    "es_festivo",
    "precio_semana_anterior",
    "tendencia_ultimos_30_dias",
    "mes",
    "año",
    "municipio_enc",
    "comarca_enc",
]


def ejecutar_entrenamiento(
    csv_path: Path,
    output_path: Path,
    min_rows: int = MIN_ROWS,
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

    X = df[FEATURE_COLUMNS].to_numpy()
    y = df[TARGET_COLUMN].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model: RandomForestRegressor = RandomForestRegressor(
        n_estimators=100, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    logger.info("MAE: %.4f", mae)
    logger.info("R²: %.4f", r2)

    artifact: dict[str, Any] = {
        "model": model,
        "label_encoder_municipio": le_municipio,
        "label_encoder_comarca": le_comarca,
        "features_names": FEATURE_COLUMNS,
        "trained_at": datetime.now(UTC).isoformat(),
        "mae": mae,
        "r2": r2,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)
    logger.info("Artifact saved: %s", output_path)

    return artifact


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
    df["mes"] = df["fecha"].dt.month
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
