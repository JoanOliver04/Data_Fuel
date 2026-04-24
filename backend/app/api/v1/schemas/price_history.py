"""Pydantic schema for price history API responses."""

from datetime import datetime

from pydantic import BaseModel


class PricePointOut(BaseModel):
    recorded_at: datetime
    price: float

    model_config = {"from_attributes": True}
