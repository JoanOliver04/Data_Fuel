"""Typed analytics DTOs (response payloads kept thin for the frontend)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TimeRange = Literal["24h", "7d", "30d", "90d", "1y"]
GroupBy = Literal["none", "brand", "comarca"]
Direction = Literal["UP", "DOWN", "STABLE"]
InsightSource = Literal["deterministic", "llm"]


class Insight(BaseModel):
    """An executive-grade one-liner derived from aggregates."""

    text: str
    source: InsightSource = "deterministic"


class TrendPoint(BaseModel):
    bucket: str  # ISO date (or hour) label for the time bucket
    avg_price: float
    min_price: float
    max_price: float
    sample_count: int


class TrendSeries(BaseModel):
    label: str  # "all" | brand | comarca
    points: list[TrendPoint]


class TrendsOut(BaseModel):
    fuel_type: str
    range: TimeRange
    group_by: GroupBy
    series: list[TrendSeries]
    insight: Insight


class ComarcaStat(BaseModel):
    comarca: str
    avg_price: float
    min_price: float
    max_price: float
    station_count: int
    sample_count: int
    delta_pct: float | None = None  # vs the previous equal window
    direction: Direction = "STABLE"


class ComarcasOut(BaseModel):
    fuel_type: str
    range: TimeRange
    items: list[ComarcaStat]
    insight: Insight


class BrandStat(BaseModel):
    brand: str
    rank: int
    avg_price: float
    station_count: int
    sample_count: int
    delta_pct: float | None = None
    direction: Direction = "STABLE"


class BrandsOut(BaseModel):
    fuel_type: str
    range: TimeRange
    items: list[BrandStat]
    insight: Insight


class HeatmapPoint(BaseModel):
    station_id: int
    lat: float
    lon: float
    brand: str
    municipality: str
    price: float


class HeatmapOut(BaseModel):
    fuel_type: str
    count: int
    min_price: float | None = None
    max_price: float | None = None
    points: list[HeatmapPoint]


class OverviewOut(BaseModel):
    generated_at: datetime
    total_stations: int
    total_observations: int
    fuel_averages: dict[str, float]
    cheapest_comarca: str | None = None
    most_expensive_comarca: str | None = None
    insight: Insight


class InsightsOut(BaseModel):
    """Bundle of headline insights for the dashboard."""

    fuel_type: str
    range: TimeRange
    items: list[Insight] = Field(default_factory=list)
