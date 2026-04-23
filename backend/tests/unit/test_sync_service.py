"""Unit tests for SyncService."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.external.miteco.schemas import MitecoApiResponse, MitecoStation
from app.services.sync_service import SyncService, _dec, _price_dicts, _station_dict


# ── helpers ────────────────────────────────────────────────────────────────


def _make_station(**overrides) -> MitecoStation:
    defaults = {
        "IDEESS": 1001,
        "Rótulo": "REPSOL",
        "Dirección": "Calle Mayor 1",
        "Localidad": "Valencia",
        "Municipio": "Valencia",
        "Provincia": "Valencia",
        "C.P.": "46001",
        "Latitud": "39,4700",
        "Longitud (WGS84)": "-0,3760",
        "Horario": "L-D: 24H",
        "Precio Gasolina 95 E5": "1,595",
        "Precio Gasolina 95 E10": "",
        "Precio Gasolina 98 E5": "1,699",
        "Precio Gasoleo A": "1,489",
        "Precio Gasoleo Premium": "",
    }
    defaults.update(overrides)
    return MitecoStation.model_validate(defaults)


# ── _dec ───────────────────────────────────────────────────────────────────


def test_dec_none():
    assert _dec(None) is None


def test_dec_float():
    assert _dec(1.595) == Decimal("1.595")


def test_dec_zero():
    assert _dec(0.0) == Decimal("0")


# ── _station_dict ──────────────────────────────────────────────────────────


def test_station_dict_basic():
    ms = _make_station()
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    row = _station_dict(ms, now)

    assert row["id"] == 1001
    assert row["brand"] == "REPSOL"
    assert row["latitude"] == 39.47
    assert row["price_gasoline_95_e5"] == Decimal("1.595")
    assert row["price_gasoline_95_e10"] is None
    assert row["updated_at"] == now


# ── _price_dicts ───────────────────────────────────────────────────────────


def test_price_dicts_only_non_null():
    ms = _make_station()
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    rows = _price_dicts(ms, now)

    fuel_types = {r["fuel_type"] for r in rows}
    # 95 E5, 98 E5, Diesel A are set; 95 E10 and Premium are empty.
    assert len(rows) == 3
    assert all(r["station_id"] == 1001 for r in rows)
    assert "gasoline_95_e10" not in fuel_types
    assert "diesel_premium" not in fuel_types


def test_price_dicts_empty_when_no_prices():
    ms = _make_station(
        **{
            "Precio Gasolina 95 E5": "",
            "Precio Gasolina 95 E10": "",
            "Precio Gasolina 98 E5": "",
            "Precio Gasoleo A": "",
            "Precio Gasoleo Premium": "",
        }
    )
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    assert _price_dicts(ms, now) == []


# ── SyncService.run ────────────────────────────────────────────────────────


@pytest.fixture
def fake_response():
    s1 = _make_station(**{"IDEESS": 1, "Latitud": "39,47", "Longitud (WGS84)": "-0,37"})
    s2 = _make_station(**{"IDEESS": 2, "Latitud": "40,41", "Longitud (WGS84)": "-3,70"})
    # Station with no coordinates — should be skipped.
    s3 = _make_station(**{"IDEESS": 3, "Latitud": "", "Longitud (WGS84)": ""})
    return MitecoApiResponse(
        **{
            "Fecha": "23/04/2026 12:00:00",
            "ListaEESSPrecio": [
                s1.model_dump(by_alias=True),
                s2.model_dump(by_alias=True),
                s3.model_dump(by_alias=True),
            ],
            "ResultadoConsulta": "OK",
        }
    )


@pytest.mark.asyncio
async def test_sync_service_run(engine, db, fake_response):
    """SyncService.run persists stations and prices; stations without coords are skipped."""
    from app.infrastructure.database import get_session_factory

    session_factory = get_session_factory()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get_all_stations = AsyncMock(return_value=fake_response)

    with patch("app.services.sync_service.MitecoClient", return_value=mock_client):
        svc = SyncService(session_factory)
        result = await svc.run()

    assert result.stations_synced == 2
    assert result.stations_skipped == 1
    assert result.prices_recorded > 0


@pytest.mark.asyncio
async def test_sync_service_idempotent(engine, db, fake_response):
    """Running sync twice does not raise — upsert handles duplicates."""
    from app.infrastructure.database import get_session_factory

    session_factory = get_session_factory()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get_all_stations = AsyncMock(return_value=fake_response)

    with patch("app.services.sync_service.MitecoClient", return_value=mock_client):
        svc = SyncService(session_factory)
        await svc.run()
        result = await svc.run()

    assert result.stations_synced == 2
