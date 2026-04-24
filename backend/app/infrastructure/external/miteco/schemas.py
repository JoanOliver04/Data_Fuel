"""Pydantic schemas matching the MITECO API response shape.

The MITECO API returns Spanish-named fields and uses comma as decimal separator
for prices and coordinates (e.g. "1,595" or "43,5421"). These schemas alias the
Spanish keys to English attributes and coerce the numeric strings to floats.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.entities.fuel_type import FuelType


def _comma_decimal_to_float(value: str | float | None) -> float | None:
    """Convert MITECO's comma-decimal strings to floats. Empty → None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return float(value.replace(",", "."))


class MitecoStation(BaseModel):
    """A single station entry from the MITECO API."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(alias="IDEESS")
    brand: str = Field(alias="Rótulo", default="")
    address: str = Field(alias="Dirección", default="")
    locality: str = Field(alias="Localidad", default="")
    municipality: str = Field(alias="Municipio", default="")
    province: str = Field(alias="Provincia", default="")
    postal_code: str = Field(alias="C.P.", default="")
    latitude: float | None = Field(alias="Latitud", default=None)
    longitude: float | None = Field(alias="Longitud (WGS84)", default=None)
    schedule: str = Field(alias="Horario", default="")

    # Prices — keys aliased from MITECO's Spanish field names.
    price_gasoline_95_e5: float | None = Field(alias="Precio Gasolina 95 E5", default=None)
    price_gasoline_95_e10: float | None = Field(alias="Precio Gasolina 95 E10", default=None)
    price_gasoline_98_e5: float | None = Field(alias="Precio Gasolina 98 E5", default=None)
    price_diesel_a: float | None = Field(alias="Precio Gasoleo A", default=None)
    price_diesel_premium: float | None = Field(alias="Precio Gasoleo Premium", default=None)

    @field_validator(
        "latitude",
        "longitude",
        "price_gasoline_95_e5",
        "price_gasoline_95_e10",
        "price_gasoline_98_e5",
        "price_diesel_a",
        "price_diesel_premium",
        mode="before",
    )
    @classmethod
    def parse_comma_decimal(cls, value: str | float | None) -> float | None:
        """Coerce '1,595' → 1.595 and '' → None."""
        return _comma_decimal_to_float(value)

    def prices_by_fuel(self) -> dict[FuelType, float | None]:
        """Return prices keyed by domain FuelType for easier downstream mapping."""
        return {
            FuelType.GASOLINA_95: self.price_gasoline_95_e5,
            FuelType.GASOLINA_95_E10: self.price_gasoline_95_e10,
            FuelType.GASOLINA_98: self.price_gasoline_98_e5,
            FuelType.GASOIL: self.price_diesel_a,
            FuelType.GASOIL_PREMIUM: self.price_diesel_premium,
        }


class MitecoApiResponse(BaseModel):
    """Top-level MITECO API response wrapper."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    fetched_at: datetime = Field(alias="Fecha")
    stations: list[MitecoStation] = Field(alias="ListaEESSPrecio", default_factory=list)
    result: str = Field(alias="ResultadoConsulta", default="")

    @field_validator("fetched_at", mode="before")
    @classmethod
    def parse_spanish_date(cls, value: str | datetime) -> datetime:
        """MITECO returns dates like '23/04/2026 13:30:00'."""
        if isinstance(value, datetime):
            return value
        return datetime.strptime(value, "%d/%m/%Y %H:%M:%S")
