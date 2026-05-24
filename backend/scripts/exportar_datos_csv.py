"""CLI wrapper for the dataset export service.

The feature-engineering logic lives in
``app.services.dataset_export_service`` (importable production code). This
script is the thin command-line entry point.

Usage (run from backend/):
    python scripts/exportar_datos_csv.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Allow `app.*` imports when executed as a top-level script from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.dataset_export_service import (
    COLUMN_ORDER,
    DEFAULT_OUTPUT_PATH,
    export_dataset,
)

# Backward-compatible aliases (imported by tests/integration/test_exportar_csv.py).
_run = export_dataset
_OUTPUT_PATH = DEFAULT_OUTPUT_PATH

__all__ = ["COLUMN_ORDER", "exportar_datos_csv"]


def exportar_datos_csv(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> Path:
    """Export price history to CSV. Pass a custom factory in tests."""
    return asyncio.run(export_dataset(output_path, factory))


if __name__ == "__main__":
    logging_format = "%(asctime)s [%(levelname)s] %(message)s"
    import logging

    logging.basicConfig(level=logging.INFO, format=logging_format, datefmt="%Y-%m-%d %H:%M:%S")
    exportar_datos_csv()
