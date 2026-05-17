"""Pydantic schemas for smart-advice responses."""

from pydantic import BaseModel

from app.domain.services.cost_calculator import StationCost
from app.domain.services.smart_refuel_service import SmartAdvice


class StationRef(BaseModel):
    station_id: int
    brand: str
    address: str
    locality: str
    province: str
    latitude: float
    longitude: float
    price_per_liter: float
    distance_km: float
    total_cost: float

    @classmethod
    def from_station_cost(cls, sc: StationCost) -> "StationRef":
        return cls(
            station_id=sc.station_id,
            brand=sc.brand,
            address=sc.address,
            locality=sc.locality,
            province=sc.province,
            latitude=sc.latitude,
            longitude=sc.longitude,
            price_per_liter=float(sc.price_per_liter),
            distance_km=sc.distance_km,
            total_cost=float(sc.total_cost),
        )


class SmartAdviceOut(BaseModel):
    action: str
    recommended_station: StationRef
    current_cost: float
    predicted_cost: float
    savings_eur: float
    savings_pct: float
    reasoning: str
    confidence: float

    @classmethod
    def from_advice(cls, advice: SmartAdvice) -> "SmartAdviceOut":
        return cls(
            action=advice.action,
            recommended_station=StationRef.from_station_cost(advice.recommended_station),
            current_cost=advice.current_cost,
            predicted_cost=advice.predicted_cost,
            savings_eur=advice.savings_eur,
            savings_pct=advice.savings_pct,
            reasoning=advice.reasoning,
            confidence=advice.confidence,
        )
