"""Pydantic schema for prediction responses."""

import dataclasses

from pydantic import BaseModel

from app.domain.entities.fuel_type import FuelType
from app.domain.services.prediction_service import PredictionResult


class PredictionOut(BaseModel):
    station_id: int
    fuel_type: str
    current_price: float
    predicted_price: float
    change_pct: float
    advice: str
    horizon_hours: int
    model_r2: float

    @classmethod
    def from_result(
        cls, station_id: int, fuel_type: FuelType, result: PredictionResult
    ) -> "PredictionOut":
        return cls(
            station_id=station_id,
            fuel_type=str(fuel_type),
            **dataclasses.asdict(result),
        )
