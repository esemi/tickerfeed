import httpx
import pytest
import respx

from app.providers.base import ProviderError, SymbolNotFoundError
from app.providers.yahoo import CHART_URL, YahooProvider, parse_chart

VOD_URL = CHART_URL.format(symbol='VOD.L')


@pytest.fixture
async def yahoo():
    async with httpx.AsyncClient() as client:
        yield YahooProvider(client, concurrency=2)


def test_parse_chart(chart_payload) -> None:
    quote = parse_chart(chart_payload)

    assert quote.symbol == 'VOD.L'
    assert quote.name == 'Vodafone Group Public Limited Company'
    assert quote.currency == 'GBp'
    assert quote.price == 116.95


def test_parse_chart_empty_result() -> None:
    payload = {'chart': {'result': None, 'error': {'code': 'Not Found'}}}

    with pytest.raises(SymbolNotFoundError):
        parse_chart(payload)


@respx.mock
async def test_fetch(yahoo, chart_payload) -> None:
    route = respx.get(VOD_URL).respond(json=chart_payload)

    quote = await yahoo.fetch('VOD.L')

    assert quote.symbol == 'VOD.L'
    assert route.call_count == 1
    assert route.calls.last.request.url.params['range'] == '1d'


@respx.mock
async def test_fetch_not_found(yahoo) -> None:
    respx.get(VOD_URL).respond(404, json={'chart': {'result': None, 'error': {'code': 'Not Found'}}})

    with pytest.raises(SymbolNotFoundError):
        await yahoo.fetch('VOD.L')


@pytest.mark.parametrize('response', [
    httpx.Response(429),
    httpx.Response(500),
    httpx.Response(200, text='<html>captcha</html>'),
    httpx.Response(200, json={'chart': {}}),
])
@respx.mock
async def test_fetch_provider_error(yahoo, response) -> None:
    respx.get(VOD_URL).mock(return_value=response)

    with pytest.raises(ProviderError):
        await yahoo.fetch('VOD.L')


@respx.mock
async def test_fetch_network_error(yahoo) -> None:
    respx.get(VOD_URL).mock(side_effect=httpx.ConnectTimeout('timeout'))

    with pytest.raises(ProviderError):
        await yahoo.fetch('VOD.L')
