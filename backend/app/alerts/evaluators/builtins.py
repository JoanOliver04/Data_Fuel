"""The eight built-in alert evaluators.

Each is a small, pure decision unit registered in the registry. All figures come
from validated platform data (rankings, prices, ML predictions) — evaluators
never invent numbers, so notifications stay trustworthy. New types slot in by
adding a class here and registering it; the engine is untouched.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.alerts.evaluators.base import Trigger
from app.alerts.evaluators.registry import register
from app.alerts.templates import direction_word, fuel_label

if TYPE_CHECKING:
    from app.alerts.evaluators.context import AlertContext
    from app.alerts.models.alert import AlertORM


async def _reference(alert: AlertORM, ctx: AlertContext) -> tuple[float, int | None, str] | None:
    """Resolve the reference (price, station_id, label) for an alert.

    Prefers an explicit station, then the cheapest within the geo radius, then
    the cheapest anywhere. ``None`` when no priced station is available.
    """
    fuel = alert.fuel_type
    if alert.station_id is not None:
        station = await ctx.station(alert.station_id)
        if station is None:
            return None
        price = ctx.station_price_now(station, fuel)
        return None if price is None else (price, station.id, f"{station.brand} ({station.locality})")
    if alert.latitude is not None and alert.longitude is not None:
        ranked = await ctx.ranked(fuel, alert.latitude, alert.longitude, alert.radius_km, alert.liters)
        if not ranked:
            return None
        best = ranked[0]
        return float(best.price_per_liter), best.station_id, f"{best.brand} ({best.locality})"
    anywhere = await ctx.cheapest_anywhere(fuel)
    if anywhere is None:
        return None
    price, station = anywhere
    return price, station.id, f"{station.brand} ({station.locality})"


class PriceBelowThresholdEvaluator:
    alert_type = "PRICE_BELOW_THRESHOLD"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.threshold_price is None:
            return None
        ref = await _reference(alert, ctx)
        if ref is None:
            return None
        price, _sid, label = ref
        target = float(alert.threshold_price)
        if price > target:
            return None
        fl = fuel_label(alert.fuel_type)
        return Trigger(
            title=f"{fl} por debajo de tu objetivo",
            message=(
                f"{fl} está a {price:.3f} €/L en {label}, por debajo de tu "
                f"objetivo de {target:.3f} €/L."
            ),
            dedup_key=f"below:{price:.3f}",
            data={"price": price, "target": target, "station": label},
        )


class PriceChangeEvaluator:
    alert_type = "PRICE_CHANGE"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.threshold_pct is None:
            return None
        ref = await _reference(alert, ctx)
        if ref is None:
            return None
        price, sid, label = ref
        if sid is None:
            return None
        base = await ctx.station_price_days_ago(sid, alert.fuel_type, days=7)
        if base is None or base <= 0:
            return None
        pct = (price - base) / base * 100
        if abs(pct) < alert.threshold_pct:
            return None
        fl = fuel_label(alert.fuel_type)
        word = direction_word(pct)
        return Trigger(
            title=f"{fl} ha {word} en {label}",
            message=(
                f"{fl} ha {word} un {abs(pct):.1f}% en {label} "
                f"(de {base:.3f} a {price:.3f} €/L) en 7 días."
            ),
            dedup_key=f"change:{price:.3f}",
            data={"price": price, "baseline": base, "change_pct": round(pct, 2), "station": label},
        )


class FavoriteStationChangeEvaluator:
    alert_type = "FAVORITE_STATION_CHANGE"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.station_id is None:
            return None
        station = await ctx.station(alert.station_id)
        if station is None:
            return None
        price = ctx.station_price_now(station, alert.fuel_type)
        if price is None:
            return None
        base = await ctx.station_price_days_ago(alert.station_id, alert.fuel_type, days=2)
        if base is None:
            return None
        delta = price - base
        if abs(delta) < 0.001:  # ignore sub-0.1c noise
            return None
        word = "bajado" if delta < 0 else "subido"
        cents = abs(delta) * 100
        fl = fuel_label(alert.fuel_type)
        label = f"{station.brand} ({station.locality})"
        return Trigger(
            title=f"Tu estación favorita ha {word} el precio",
            message=f"{label}: {fl} ha {word} {cents:.0f} céntimos (ahora {price:.3f} €/L).",
            dedup_key=f"fav:{price:.3f}",
            data={"price": price, "baseline": base, "delta": round(delta, 3), "station": label},
        )


class CheapestBrandEvaluator:
    alert_type = "CHEAPEST_BRAND"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.brand is None or alert.latitude is None or alert.longitude is None:
            return None
        ranked = await ctx.ranked(
            alert.fuel_type, alert.latitude, alert.longitude, alert.radius_km, alert.liters
        )
        if not ranked:
            return None
        best = ranked[0]
        if best.brand.upper() != alert.brand.upper():
            return None
        fl = fuel_label(alert.fuel_type)
        price = float(best.price_per_liter)
        return Trigger(
            title=f"{best.brand} es la más barata cerca",
            message=(
                f"{best.brand} en {best.locality} es la estación más barata en "
                f"{alert.radius_km:.0f} km para {fl}: {price:.3f} €/L."
            ),
            dedup_key=f"cheapest:{best.station_id}",
            data={"brand": best.brand, "price": price, "station_id": best.station_id},
        )


class WeeklySummaryEvaluator:
    alert_type = "WEEKLY_SUMMARY"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        ref = await _reference(alert, ctx)
        if ref is None:
            return None
        price, sid, label = ref
        fl = fuel_label(alert.fuel_type)
        trend = ""
        base = (
            await ctx.station_price_days_ago(sid, alert.fuel_type, days=7)
            if sid is not None
            else None
        )
        if base is not None and base > 0:
            pct = (price - base) / base * 100
            word = direction_word(pct)
            trend = (
                " Esta semana se ha mantenido estable."
                if word == "sin cambios"
                else f" Esta semana ha {word} un {abs(pct):.1f}%."
            )
        iso = datetime.now(UTC).isocalendar()
        return Trigger(
            title=f"Resumen semanal de {fl}",
            message=f"La opción más barata para {fl} es {label} a {price:.3f} €/L.{trend}",
            dedup_key=f"week:{iso.year}-{iso.week:02d}",
            data={"price": price, "station": label},
        )


class WaitVsRefuelEvaluator:
    alert_type = "WAIT_VS_REFUEL_SIGNAL"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.threshold_pct is None or alert.latitude is None or alert.longitude is None:
            return None
        pred = await ctx.predict(
            alert.fuel_type, alert.latitude, alert.longitude, alert.radius_km, alert.liters
        )
        if pred is None or pred.change_pct >= 0:  # only worth waiting if a drop is forecast
            return None
        save_pct = abs(pred.change_pct)
        if save_pct < alert.threshold_pct:
            return None
        days = max(1, round(pred.horizon_hours / 24))
        fl = fuel_label(alert.fuel_type)
        return Trigger(
            title="Quizá compense esperar",
            message=(
                f"Esperar ~{days} día(s) podría ahorrar aproximadamente un {save_pct:.1f}% "
                f"en {fl}, según la predicción (confianza {pred.model_r2:.0%})."
            ),
            dedup_key=f"wait:{save_pct:.1f}",
            data={
                "save_pct": round(save_pct, 2),
                "horizon_hours": pred.horizon_hours,
                "model_r2": pred.model_r2,
            },
        )


class PredictionTrendEvaluator:
    alert_type = "PREDICTION_TREND"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.latitude is None or alert.longitude is None:
            return None
        pred = await ctx.predict(
            alert.fuel_type, alert.latitude, alert.longitude, alert.radius_km, alert.liters
        )
        if pred is None:
            return None
        threshold = alert.threshold_pct if alert.threshold_pct is not None else 0.5
        if abs(pred.change_pct) < threshold:
            return None
        fl = fuel_label(alert.fuel_type)
        word = "subir" if pred.change_pct > 0 else "bajar"
        return Trigger(
            title=f"Se prevé que {fl} va a {word}",
            message=(
                f"Se prevé que {fl} va a {word} aproximadamente un {abs(pred.change_pct):.1f}% "
                f"en {pred.horizon_hours}h (confianza {pred.model_r2:.0%})."
            ),
            dedup_key=f"trend:{pred.change_pct:.1f}",
            data={
                "change_pct": pred.change_pct,
                "horizon_hours": pred.horizon_hours,
                "model_r2": pred.model_r2,
            },
        )


class TotalCostDropEvaluator:
    alert_type = "TOTAL_COST_DROP"

    async def evaluate(self, alert: AlertORM, ctx: AlertContext) -> Trigger | None:
        if alert.threshold_pct is None or alert.latitude is None or alert.longitude is None:
            return None
        ranked = await ctx.ranked(
            alert.fuel_type, alert.latitude, alert.longitude, alert.radius_km, alert.liters
        )
        if not ranked or ranked[0].station_id is None:
            return None
        best = ranked[0]
        prev_price = await ctx.station_price_days_ago(best.station_id, alert.fuel_type, days=1)
        if prev_price is None:
            return None
        now_total = float(best.total_cost)
        prev_total = prev_price * alert.liters + float(best.travel_cost)
        if prev_total <= 0:
            return None
        pct = (now_total - prev_total) / prev_total * 100
        if pct > -alert.threshold_pct:  # only fire on a real drop
            return None
        fl = fuel_label(alert.fuel_type)
        return Trigger(
            title="El coste total real ha bajado",
            message=(
                f"El coste total (combustible + desplazamiento) de {fl} en "
                f"{best.brand} ({best.locality}) ha bajado un {abs(pct):.1f}% frente a ayer: "
                f"ahora {now_total:.2f} €."
            ),
            dedup_key=f"cost:{now_total:.2f}",
            data={
                "total_now": round(now_total, 2),
                "total_prev": round(prev_total, 2),
                "change_pct": round(pct, 2),
            },
        )


# Register all built-ins (instances satisfy the AlertEvaluator Protocol).
for _evaluator in (
    PriceBelowThresholdEvaluator(),
    PriceChangeEvaluator(),
    FavoriteStationChangeEvaluator(),
    CheapestBrandEvaluator(),
    WeeklySummaryEvaluator(),
    WaitVsRefuelEvaluator(),
    PredictionTrendEvaluator(),
    TotalCostDropEvaluator(),
):
    register(_evaluator)
