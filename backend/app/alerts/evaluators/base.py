"""Evaluator contract + trigger result.

An evaluator is a pure decision unit: given an alert and a shared per-batch
:class:`AlertContext`, it returns a :class:`Trigger` when the alert fires, or
``None``. It never persists, sends, or mutates the alert — orchestration owns
that. Adding an alert type = a new evaluator registered in the registry, with no
change to the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.alerts.schemas import TriggerSource

if TYPE_CHECKING:
    from app.alerts.evaluators.context import AlertContext
    from app.alerts.models.alert import AlertORM


@dataclass(frozen=True, slots=True)
class Trigger:
    """A fired alert. ``dedup_key`` is the *trigger-state* signature (e.g. the
    rounded price/date); the dispatcher namespaces it with the alert id."""

    title: str
    message: str
    dedup_key: str
    data: dict[str, object] = field(default_factory=dict)
    source: TriggerSource = "deterministic"


@runtime_checkable
class AlertEvaluator(Protocol):
    """Decides whether one alert fires. Pure and side-effect free."""

    alert_type: str

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        """Return a :class:`Trigger` if the alert fires, else ``None``."""
        ...
