"""Yahoo Finance provider via unofficial v8/chart endpoint (no crumb required)."""
import asyncio
from typing import Any

import httpx

from app.models import Quote
from app.providers.base import ProviderError, SymbolNotFoundError

CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'


class YahooProvider:
    """Yahoo Finance quotes provider."""

    def __init__(self, client: httpx.AsyncClient, concurrency: int) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(concurrency)

    async def fetch(self, symbol: str) -> Quote:
        """Fetch a quote for the Yahoo symbol."""
        async with self._semaphore:
            try:
                response = await self._client.get(
                    CHART_URL.format(symbol=symbol),
                    params={'range': '1d', 'interval': '1d'},
                )
            except httpx.HTTPError as exc:
                raise ProviderError(f'yahoo request failed: {exc!r}') from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise SymbolNotFoundError(symbol)
        if response.status_code != httpx.codes.OK:
            raise ProviderError(f'yahoo responded {response.status_code}')

        try:
            return parse_chart(response.json())
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f'unexpected yahoo payload: {exc!r}') from exc


def parse_chart(payload: dict[str, Any]) -> Quote:
    """Build a Quote from v8/chart response."""
    results = payload['chart']['result']
    if not results:
        raise SymbolNotFoundError(str(payload['chart'].get('error')))

    meta = results[0]['meta']
    return Quote(
        symbol=meta['symbol'],
        name=meta.get('longName') or meta.get('shortName'),
        currency=meta.get('currency'),
        price=meta.get('regularMarketPrice'),
    )
