"""Quotes service: symbol mapping, cache, single-flight fetching, stale fallback."""
import asyncio
import logging
from dataclasses import dataclass

from app.cache import QuoteCache, utcnow
from app.models import CachedQuote, Quote, QuoteResult
from app.providers.base import ProviderError, QuoteProvider, SymbolNotFoundError
from app.symbols import to_yahoo

logger = logging.getLogger(__name__)

ERROR_NOT_FOUND = 'symbol not found'
ERROR_PROVIDER = 'provider unavailable'


@dataclass(frozen=True)
class CacheTtl:
    """Cache lifetimes in seconds."""

    fresh: int
    stale: int
    not_found: int


@dataclass(frozen=True)
class _Lookup:
    quote: Quote | None
    stale: bool = False
    error: str | None = None


class QuoteService:
    """Resolves GOOGLEFINANCE-like queries into quotes."""

    def __init__(self, provider: QuoteProvider, cache: QuoteCache, ttl: CacheTtl) -> None:
        self._provider = provider
        self._cache = cache
        self._ttl = ttl
        self._inflight: dict[str, asyncio.Task[_Lookup]] = {}

    async def get_quotes(self, queries: list[str], in_pounds: bool = False) -> list[QuoteResult]:
        """Return results in the same order as queries."""
        symbols: dict[str, str] = {}
        results: dict[str, QuoteResult] = {}
        for query in queries:
            try:
                symbols[query] = to_yahoo(query)
            except ValueError as exc:
                results[query] = QuoteResult(query=query, error=str(exc))

        lookups = await self._lookup_many(sorted(set(symbols.values())))
        for query, symbol in symbols.items():
            lookup = lookups[symbol]
            quote = lookup.quote.in_pounds() if lookup.quote and in_pounds else lookup.quote
            results[query] = QuoteResult(query=query, quote=quote, stale=lookup.stale, error=lookup.error)

        return [results[query] for query in queries]

    async def _lookup_many(self, symbols: list[str]) -> dict[str, _Lookup]:
        cached = await self._cache.get_many(symbols)
        lookups: dict[str, _Lookup] = {}
        to_fetch: list[str] = []
        for symbol in symbols:
            entry = cached.get(symbol)
            if entry is not None and entry.quote is None:
                lookups[symbol] = _Lookup(quote=None, error=ERROR_NOT_FOUND)
            elif entry is not None and self._is_fresh(entry):
                lookups[symbol] = _Lookup(quote=entry.quote)
            else:
                to_fetch.append(symbol)

        fetched = await asyncio.gather(*(self._fetch_once(symbol, cached.get(symbol)) for symbol in to_fetch))
        lookups.update(zip(to_fetch, fetched, strict=True))
        return lookups

    def _is_fresh(self, entry: CachedQuote) -> bool:
        return (utcnow() - entry.fetched_at).total_seconds() < self._ttl.fresh

    async def _fetch_once(self, symbol: str, stale: CachedQuote | None) -> _Lookup:
        """Single-flight: concurrent requests for one symbol share a provider call."""
        task = self._inflight.get(symbol)
        if task is None:
            task = asyncio.create_task(self._fetch(symbol, stale))
            self._inflight[symbol] = task
            task.add_done_callback(lambda _: self._inflight.pop(symbol, None))
        return await asyncio.shield(task)

    async def _fetch(self, symbol: str, stale: CachedQuote | None) -> _Lookup:
        try:
            quote = await self._provider.fetch(symbol)
        except SymbolNotFoundError:
            await self._cache.put(symbol, CachedQuote(fetched_at=utcnow()), ttl=self._ttl.not_found)
            return _Lookup(quote=None, error=ERROR_NOT_FOUND)
        except ProviderError as exc:
            logger.warning('provider failed for %s: %s', symbol, exc)
            if stale is not None and stale.quote is not None:
                return _Lookup(quote=stale.quote, stale=True)
            return _Lookup(quote=None, error=ERROR_PROVIDER)

        await self._cache.put(symbol, CachedQuote(fetched_at=utcnow(), quote=quote), ttl=self._ttl.stale)
        return _Lookup(quote=quote)
