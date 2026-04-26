"""GeoJSON response schemas for the price heatmap endpoint."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class HeatmapProperties(BaseModel):
    id: int
    price: Decimal
    price_normalized: float
    brand: str
    name: str


class HeatmapGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    # GeoJSON convention: [longitude, latitude] (RFC 7946 §3.1.1).
    coordinates: tuple[float, float]


class HeatmapFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: HeatmapGeometry
    properties: HeatmapProperties


class HeatmapFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[HeatmapFeature]
