"""Shared Spanish national-holiday calendar used by both the export pipeline
and the inference service.

Only fixed-date holidays are included; movable ones (e.g. Easter) are
intentionally excluded so the mapping stays deterministic and reproducible
across training and inference.
"""

from __future__ import annotations

from datetime import date, datetime

HOLIDAYS_ES_FIXED: frozenset[tuple[int, int]] = frozenset({
    (1, 1),    # Año Nuevo
    (1, 6),    # Reyes
    (5, 1),    # Día del Trabajo
    (8, 15),   # Asunción
    (10, 12),  # Fiesta Nacional
    (11, 1),   # Todos los Santos
    (12, 6),   # Constitución
    (12, 8),   # Inmaculada
    (12, 25),  # Navidad
})


def is_festivo(d: date | datetime) -> int:
    """Return 1 if d is a weekend or fixed Spanish national holiday, else 0."""
    if d.weekday() >= 5:
        return 1
    if (d.month, d.day) in HOLIDAYS_ES_FIXED:
        return 1
    return 0
