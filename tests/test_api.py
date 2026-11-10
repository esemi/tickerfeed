import httpx
import pytest

from app.api import app, build_http_client
from app.settings import app_settings

API_KEY = 'test-key'


@pytest.fixture
async def client(mocker, service):
    mocker.patch.object(app_settings, 'api_key', API_KEY)
    app.state.service = service
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as http_client:
        yield http_client


async def test_quotes(client, provider, quote_ko) -> None:
    provider.quotes['KO'] = quote_ko

    response = await client.get('/v1/quotes', params={'symbols': 'NYSE:KO, LSE:NOPE'}, headers={'X-Api-Key': API_KEY})

    body = response.json()
    assert response.status_code == 200
    assert [result['query'] for result in body['results']] == ['NYSE:KO', 'LSE:NOPE']
    assert body['results'][0]['quote']['price'] == 95.72
    assert body['results'][1]['error'] == 'symbol not found'


@pytest.mark.parametrize('headers', [{}, {'X-Api-Key': 'wrong'}, {'X-Api-Key': '<ключ>'.encode()}])
async def test_quotes_unauthorized(client, headers) -> None:
    response = await client.get('/v1/quotes', params={'symbols': 'NYSE:KO'}, headers=headers)

    assert response.status_code == 401


@pytest.mark.parametrize('symbols', [' , ', ','.join(['KO'] * 201)])
async def test_quotes_bad_symbols(client, symbols) -> None:
    response = await client.get('/v1/quotes', params={'symbols': symbols}, headers={'X-Api-Key': API_KEY})

    assert response.status_code == 422


async def test_health(client) -> None:
    response = await client.get('/health')

    assert response.status_code == 200


@pytest.mark.parametrize('proxy', [None, 'socks5://user:pass@proxy:1080'])
def test_build_http_client(mocker, proxy) -> None:
    mocker.patch.object(app_settings, 'http_proxy', proxy)
    client_mock = mocker.patch('app.api.httpx.AsyncClient')

    build_http_client()

    assert client_mock.call_count == 1
    assert client_mock.call_args.kwargs['proxy'] == proxy
