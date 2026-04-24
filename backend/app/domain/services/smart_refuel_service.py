"""Domain service: smart refuelling advisor.

Decision logic:
  1. Receive best current station (already ranked by cost_calculator).
  2. Compare with 48h predicted cost for the same station.
  3. If waiting saves > SAVINGS_THRESHOLD_EUR → advise WAIT.
  4. Otherwise → advise REFUEL_NOW.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.services.cost_calculator import StationCost
from app.domain.services.prediction_service import PredictionResult

SAVINGS_THRESHOLD_EUR: float = 2.0


@dataclass(frozen=True, slots=True)
class SmartAdvice:
    action: str  # "REFUEL_NOW" | "WAIT"
    recommended_station: StationCost
    current_cost: float
    predicted_cost: float
    savings_eur: float
    savings_pct: float
    reasoning: str
    confidence: float  # 0.0 – 1.0


class SmartRefuelService:
    """Produces a REFUEL_NOW / WAIT decision from ranked station + prediction."""

    def advise(
        self,
        best_station: StationCost,
        prediction: PredictionResult | None,
        liters: float,
        km_cost: float,  # noqa: ARG002  (kept for API consistency)
    ) -> SmartAdvice:
        current_cost = float(best_station.total_cost)

        if prediction is None:
            return SmartAdvice(
                action="REFUEL_NOW",
                recommended_station=best_station,
                current_cost=round(current_cost, 2),
                predicted_cost=round(current_cost, 2),
                savings_eur=0.0,
                savings_pct=0.0,
                reasoning=(
                    "Sin datos de predicción disponibles. "
                    "Repostar ahora en la mejor gasolinera es tu opción más segura."
                ),
                confidence=0.4,
            )

        # Predicted total = new fuel cost + unchanged travel cost
        travel_cost = float(best_station.travel_cost)
        predicted_fuel = liters * prediction.predicted_price
        predicted_cost = predicted_fuel + travel_cost

        savings = current_cost - predicted_cost
        savings_pct = round(savings / current_cost * 100, 1) if current_cost > 0 else 0.0
        confidence = round(min(0.95, max(0.1, prediction.model_r2)), 2)

        if savings > SAVINGS_THRESHOLD_EUR:
            action = "WAIT"
            reasoning = _wait_msg(savings)
        else:
            action = "REFUEL_NOW"
            reasoning = _refuel_msg(savings, prediction.change_pct)

        return SmartAdvice(
            action=action,
            recommended_station=best_station,
            current_cost=round(current_cost, 2),
            predicted_cost=round(predicted_cost, 2),
            savings_eur=round(savings, 2),
            savings_pct=savings_pct,
            reasoning=reasoning,
            confidence=confidence,
        )


# ── Human-readable message builders ─────────────────────────────────────────

def _wait_msg(savings: float) -> str:
    return f"El precio bajará en las próximas 48h. Esperar te ahorra ~{savings:.0f}€."


def _refuel_msg(savings: float, change_pct: float) -> str:
    if change_pct >= 0.5:
        return f"El precio subirá un {change_pct:.1f}% en 48h. Mejor repostar ahora."
    if savings < -0.5:
        abs_loss = abs(savings)
        return (
            f"Esperar costaría {abs_loss:.2f}€ más. Repostar ahora es la mejor opción."
        )
    return "La diferencia es mínima. Repostar ahora es la mejor opción."
