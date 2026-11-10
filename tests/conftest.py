import json
from pathlib import Path
from typing import Any

import fakeredis
import pytest

from app.cache import QuoteCache
from app.models import Quote
from app.providers.base import ProviderError, SymbolNotFoundError
from app.service import CacheTtl, QuoteService

FIXTURES = Path(__file__).parent / 'fixtures'


class FakeProvider:
    """Provider stub: returns prepared quotes, raises prepared errors, counts calls."""

    def __init__(self) -> None:
        self.quotes: dict[str, Quote] = {}
        self.failing: set[str] = set()
        self.calls: list[str] = []

    async def fetch(self, symbol: str) -> Quote:
        self.calls.append(symbol)
        if symbol in self.failing:
            raise ProviderError('boom')
        if symbol not in self.quotes:
            raise SymbolNotFoundError(symbol)
        return self.quotes[symbol]


@pytest.fixture
def chart_payload() -> dict[str, Any]:
    return json.loads((FIXTURES / 'chart_vod_l.json').read_text())


@pytest.fixture
def quote_ko() -> Quote:
    return Quote(symbol='KO', currency='USD', price=95.72)


@pytest.fixture
async def redis():
    client = fakeredis.FakeAsyncRedis()
    yield client
    await client.aclose()


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def cache(redis) -> QuoteCache:
    return QuoteCache(redis)


@pytest.fixture
def service(provider, cache) -> QuoteService:
    return QuoteService(provider=provider, cache=cache, ttl=CacheTtl(fresh=900, stale=86400, not_found=3600))
