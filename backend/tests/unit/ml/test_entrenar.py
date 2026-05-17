"""Unit tests for app.ml.training.entrenar — output contract only, no accuracy checks."""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import joblib
import pandas as pd
import pytest

from app.ml.training.entrenar import ejecutar_entrenamiento

_MUNICIPIOS = ["Valencia", "Alzira", "Madrid", "Barcelona", "Sevilla"]
_COMARCAS = ["Horta", "Ribera Alta", "Madrid", "Barcelona", "Sevilla"]
_COLS = [
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


def _make_csv(path: Path, n: int = 110) -> Path:
    """Synthetic 11-col CSV in the strict order expected by entrenar.py."""
    rng = random.Random(42)
    base = date(2026, 1, 1)
    rows = []
    for i in range(n):
        precio = round(rng.uniform(1.2, 1.8), 3)
        d = base + timedelta(days=i % 30)
        rows.append(
            {
                "fecha": d,
                "precio": precio,
                "municipio": rng.choice(_MUNICIPIOS),
                "distancia": round(rng.uniform(5, 200), 4),
                "tipo_combustible": rng.randint(1, 5),
                "comarca": rng.choice(_COMARCAS),
                "dia_de_la_semana": d.weekday(),
                "es_festivo": 1 if d.weekday() >= 5 else 0,
                "precio_semana_anterior": round(precio + rng.uniform(-0.05, 0.05), 3),
                "tendencia_ultimos_30_dias": round(rng.uniform(-0.05, 0.05), 6),
                "precio_prox_semana": round(precio + rng.uniform(-0.05, 0.05), 3),
            }
        )
    pd.DataFrame(rows, columns=_COLS).to_csv(path, index=False)
    return path


def test_pkl_created(tmp_path: Path) -> None:
    csv = _make_csv(tmp_path / "datos.csv")
    pkl = tmp_path / "modelo.pkl"
    ejecutar_entrenamiento(csv, pkl)
    assert pkl.exists()


def test_artifact_keys(tmp_path: Path) -> None:
    csv = _make_csv(tmp_path / "datos.csv")
    artifact = ejecutar_entrenamiento(csv, tmp_path / "modelo.pkl")
    expected = {
        "model",
        "label_encoder_municipio",
        "label_encoder_comarca",
        "features_names",
        "trained_at",
        "mae",
        "r2",
    }
    assert set(artifact.keys()) == expected


def test_model_has_predict(tmp_path: Path) -> None:
    csv = _make_csv(tmp_path / "datos.csv")
    artifact = ejecutar_entrenamiento(csv, tmp_path / "modelo.pkl")
    assert callable(getattr(artifact["model"], "predict", None))


def test_artifact_loaded_from_disk_matches(tmp_path: Path) -> None:
    csv = _make_csv(tmp_path / "datos.csv")
    pkl = tmp_path / "modelo.pkl"
    returned = ejecutar_entrenamiento(csv, pkl)
    loaded = joblib.load(pkl)
    assert set(loaded.keys()) == set(returned.keys())


def test_validation_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ejecutar_entrenamiento(tmp_path / "nonexistent.csv", tmp_path / "out.pkl")


def test_validation_too_few_rows(tmp_path: Path) -> None:
    csv = _make_csv(tmp_path / "datos.csv", n=50)
    with pytest.raises(ValueError, match="rows"):
        ejecutar_entrenamiento(csv, tmp_path / "out.pkl", min_rows=100)
