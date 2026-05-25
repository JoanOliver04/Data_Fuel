"""Evaluator registry — the seam that keeps alert types pluggable.

The engine looks up an evaluator by ``alert_type``; adding a type means writing
an evaluator and registering it here, with zero orchestration changes.
"""

from __future__ import annotations

from app.alerts.evaluators.base import AlertEvaluator

_REGISTRY: dict[str, AlertEvaluator] = {}


def register(evaluator: AlertEvaluator) -> AlertEvaluator:
    """Register an evaluator under its ``alert_type``. Returns it (decorator-friendly)."""
    _REGISTRY[evaluator.alert_type] = evaluator
    return evaluator


def get_evaluator(alert_type: str) -> AlertEvaluator | None:
    return _REGISTRY.get(alert_type)


def registered_types() -> list[str]:
    return sorted(_REGISTRY)
