"""Tests for MitecoClient using httpx.MockTransport (no real network)."""

import json

import httpx
import pytest

from app.infrastructure.external.miteco import MitecoClient, MitecoClientError


def _sample_payload() -> dict[str, object]:
    return {
        "Fecha": "23/04/2026 14:00:00",
        "ListaEESSPrecio": [
            {
                "IDEESS": "1",
                "Rótulo": "REPSOL",
                "Dirección": "C/ Mayor 1",
                "Localidad": "Madrid",
                "Municipio": "Madrid",
                "Provincia": "MADRID",
                "C.P.": "28001",
                "Latitud": "40,4",
                "Longitud (WGS84)": "-3,7",
                "Horario": "L-D: 24H",
                "Precio Gasolina 95 E5": "1,595",
                "Precio Gasoleo A": "1,499",
            },
        ],
        "ResultadoConsulta": "OK",
    }


def _build_mock_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, base_url="https://miteco.test")


async def test_get_all_stations_success() -> None:
    payload = _sample_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/EstacionesTerrestres/"
        return httpx.Response(200, content=json.dumps(payload).encode("utf-8"))

    transport = httpx.MockTransport(handler)
    mock_client = _build_mock_client(transport)
    try:
        async with MitecoClient(client=mock_client) as client:
            response = await client.get_all_stations()
    finally:
        await mock_client.aclose()

    assert len(response.stations) == 1
    station = response.stations[0]
    assert station.id == 1
    assert station.brand == "REPSOL"
    assert station.latitude == 40.4
    assert station.price_gasoline_95_e5 == 1.595


async def test_http_error_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with MitecoClient(client=mock_client) as client:
            with pytest.raises(MitecoClientError, match="MITECO request failed"):
                await client.get_all_stations()
    finally:
        await mock_client.aclose()


async def test_invalid_json_wrapped_as_client_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    try:
        async with MitecoClient(client=mock_client) as client:
            with pytest.raises(MitecoClientError, match="Could not parse"):
                await client.get_all_stations()
    finally:
        await mock_client.aclose()


async def test_calling_without_context_manager_raises() -> None:
    client = MitecoClient()
    with pytest.raises(MitecoClientError, match="not initialised"):
        await client.get_all_stations()


async def test_external_client_is_not_closed_on_exit() -> None:
    """When a client is injected, the caller owns its lifecycle."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(_sample_payload()).encode("utf-8"))

    mock_client = _build_mock_client(httpx.MockTransport(handler))
    async with MitecoClient(client=mock_client) as client:
        await client.get_all_stations()

    # Still usable after MitecoClient context exit.
    assert not mock_client.is_closed
    await mock_client.aclose()
