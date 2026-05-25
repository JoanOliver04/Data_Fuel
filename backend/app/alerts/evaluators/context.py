"""Per-batch shared computation context for alert evaluation.

Built once per batch tick and passed to every evaluator. It memoises expensive,
shared reads (station list, rankings, predictions, history) so a batch of alerts
over the same fuel/area does the work once. All ORM access goes through one
async session; the CPU-bound ML prediction runs in a worker thread so it never
blocks the event loop.

The context only *reads* the recommendation/prediction layers' public callables
— it never reaches into their internals.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import StationCost, price_for, rank_stations
from app.domain.services.prediction_service import PredictionResult, PredictionService, TrainingRow
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.infrastructure.database.models.station import StationORM


def _round_key(fuel: str, lat: float, lon: float, radius: float, liters: float) -> str:
    return f"{fuel}:{lat:.3f}:{lon:.3f}:{radius:.1f}:{liters:.0f}"


class AlertContext:
    """Memoised data access shared by all evaluators in one batch."""

    def __init__(
        self, session: AsyncSession, prediction_service: PredictionService, *, km_cost: float
    ) -> None:
        self._session = session
        self._prediction = prediction_service
        self._km_cost = km_cost
        self._stations: Sequence[StationORM] | None = None
        self._ranked: dict[str, list[StationCost]] = {}
        self._predictions: dict[str, PredictionResult | None] = {}
        self._training: dict[str, list[TrainingRow]] = {}

    async def _all_stations(self) -> Sequence[StationORM]:
        if self._stations is None:
            self._stations = await StationRepository(self._session).list_all()
        return self._stations

    async def ranked(
        self, fuel: str, lat: float, lon: float, radius: float, liters: float
    ) -> list[StationCost]:
        """Stations within ``radius`` ranked by total cost (cheapest first)."""
        key = _round_key(fuel, lat, lon, radius, liters)
        cached = self._ranked.get(key)
        if cached is not None:
            return cached
        stations = await self._all_stations()
        ranked = rank_stations(
            stations=stations,
            fuel_type=FuelType(fuel),
            user_lat=lat,
            user_lon=lon,
            liters=liters,
            km_cost=self._km_cost,
            max_distance_km=radius,
            limit=10,
        )
        self._ranked[key] = ranked
        return ranked

    async def station(self, station_id: int) -> StationORM | None:
        return await StationRepository(self._session).get_by_id(station_id)

    async def cheapest_anywhere(self, fuel: str) -> tuple[float, StationORM] | None:
        """Lowest current price for ``fuel`` across all stations (no geo filter)."""
        best: tuple[float, StationORM] | None = None
        for station in await self._all_stations():
            price = self.station_price_now(station, fuel)
            if price is None:
                continue
            if best is None or price < best[0]:
                best = (price, station)
        return best

    def station_price_now(self, station: StationORM, fuel: str) -> float | None:
        price = price_for(station, FuelType(fuel))
        return float(price) if price is not None else None

    async def station_price_days_ago(
        self, station_id: int, fuel: str, *, days: int
    ) -> float | None:
        """Oldest recorded price within the last ``days`` (the baseline to compare)."""
        history = await PriceRepository(self._session).get_price_history(
            station_id, FuelType(fuel), days=days
        )
        return float(history[0]["price"]) if history else None

    async def predict(
        self, fuel: str, lat: float, lon: float, radius: float, liters: float
    ) -> PredictionResult | None:
        """Forecast for the cheapest station in the area. Runs ML off the loop."""
        key = _round_key(fuel, lat, lon, radius, liters)
        if key in self._predictions:
            return self._predictions[key]
        ranked = await self.ranked(fuel, lat, lon, radius, liters)
        if not ranked:
            self._predictions[key] = None
            return None
        best = ranked[0]
        rows = await self._training_rows(fuel)
        result = await asyncio.to_thread(
            self._prediction.predict,
            rows=rows,
            current_price=float(best.price_per_liter),
            brand=best.brand,
            province=best.province,
            fuel_type=FuelType(fuel),
        )
        self._predictions[key] = result
        return result

    async def _training_rows(self, fuel: str) -> list[TrainingRow]:
        cached = self._training.get(fuel)
        if cached is not None:
            return cached
        raw = await PriceRepository(self._session).get_training_data(FuelType(fuel))
        rows = [TrainingRow(**r) for r in raw]
        self._training[fuel] = rows
        return rows
