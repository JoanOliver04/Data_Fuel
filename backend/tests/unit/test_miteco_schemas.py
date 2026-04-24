"""Tests for MITECO Pydantic schemas: Spanish aliases, comma-decimal, dates."""

from datetime import datetime

import pytest

from app.domain.entities import FuelType
from app.infrastructure.external.miteco.schemas import MitecoApiResponse, MitecoStation


def _raw_station(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "IDEESS": "4375",
        "Rótulo": "REPSOL",
        "Dirección": "AVENIDA CASTILLA LA MANCHA, 26",
        "Localidad": "Abengibre",
        "Municipio": "Abengibre",
        "Provincia": "ALBACETE",
        "C.P.": "02250",
        "Latitud": "39,211417",
        "Longitud (WGS84)": "-1,539167",
        "Horario": "L-D: 07:00-22:00",
        "Precio Gasolina 95 E5": "1,479",
        "Precio Gasolina 95 E10": "",
        "Precio Gasolina 98 E5": "",
        "Precio Gasoleo A": "1,689",
        "Precio Gasoleo Premium": "",
    }
    base.update(overrides)
    return base


def test_station_parses_spanish_aliases_and_comma_decimals() -> None:
    station = MitecoStation.model_validate(_raw_station())

    assert station.id == 4375
    assert station.brand == "REPSOL"
    assert station.address == "AVENIDA CASTILLA LA MANCHA, 26"
    assert station.municipality == "Abengibre"
    assert station.postal_code == "02250"
    assert station.latitude == 39.211417
    assert station.longitude == -1.539167


def test_empty_price_string_becomes_none() -> None:
    station = MitecoStation.model_validate(_raw_station())

    assert station.price_gasoline_95_e5 == 1.479
    assert station.price_diesel_a == 1.689
    assert station.price_gasoline_95_e10 is None
    assert station.price_gasoline_98_e5 is None
    assert station.price_diesel_premium is None


def test_prices_by_fuel_returns_full_mapping() -> None:
    station = MitecoStation.model_validate(_raw_station())
    prices = station.prices_by_fuel()

    assert set(prices) == set(FuelType)
    assert prices[FuelType.GASOLINA_95] == 1.479
    assert prices[FuelType.GASOIL] == 1.689
    assert prices[FuelType.GASOIL_PREMIUM] is None


def test_validator_accepts_native_floats() -> None:
    """Pydantic should pass numeric values through the validator unchanged."""
    raw = _raw_station(Latitud=40.4, **{"Precio Gasoleo A": 1.5})
    station = MitecoStation.model_validate(raw)

    assert station.latitude == 40.4
    assert station.price_diesel_a == 1.5


def test_response_parses_spanish_date() -> None:
    payload = {
        "Fecha": "23/04/2026 14:00:52",
        "ListaEESSPrecio": [_raw_station()],
        "ResultadoConsulta": "OK",
    }
    response = MitecoApiResponse.model_validate(payload)

    assert response.fetched_at == datetime(2026, 4, 23, 14, 0, 52)
    assert response.result == "OK"
    assert len(response.stations) == 1
    assert response.stations[0].id == 4375


def test_response_invalid_date_raises() -> None:
    with pytest.raises(ValueError):
        MitecoApiResponse.model_validate(
            {"Fecha": "not-a-date", "ListaEESSPrecio": [], "ResultadoConsulta": ""},
        )


def test_response_accepts_datetime_object_directly() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0)
    response = MitecoApiResponse.model_validate(
        {"Fecha": now, "ListaEESSPrecio": [], "ResultadoConsulta": ""},
    )
    assert response.fetched_at == now
