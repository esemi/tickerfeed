import asyncio
from datetime import timedelta

from app.cache import utcnow
from app.models import CachedQuote, Quote
from app.service import ERROR_NOT_FOUND, ERROR_PROVIDER


async def test_get_quotes_cache_miss(service, provider, cache, quote_ko) -> None:
    provider.quotes['KO'] = quote_ko

    results = await service.get_quotes(['NYSE:KO'])

    cached = await cache.get_many(['KO'])
    assert [result.quote for result in results] == [quote_ko]
    assert results[0].stale is False
    assert provider.calls == ['KO']
    assert cached['KO'].quote == quote_ko


async def test_get_quotes_cache_fresh(service, provider, cache, quote_ko) -> None:
    await cache.put('KO', CachedQuote(fetched_at=utcnow() - timedelta(minutes=14), quote=quote_ko), ttl=60)

    results = await service.get_quotes(['NYSE:KO'])

    assert results[0].quote == quote_ko
    assert provider.calls == []


async def test_get_quotes_cache_expired(service, provider, cache, quote_ko) -> None:
    old_quote = quote_ko.model_copy(update={'price': 1.0})
    await cache.put('KO', CachedQuote(fetched_at=utcnow() - timedelta(minutes=16), quote=old_quote), ttl=60)
    provider.quotes['KO'] = quote_ko

    results = await service.get_quotes(['NYSE:KO'])

    assert results[0].quote == quote_ko
    assert provider.calls == ['KO']


async def test_get_quotes_provider_error_stale(service, provider, cache, quote_ko) -> None:
    await cache.put('KO', CachedQuote(fetched_at=utcnow() - timedelta(hours=3), quote=quote_ko), ttl=60)
    provider.failing.add('KO')

    results = await service.get_quotes(['NYSE:KO'])

    assert results[0].quote == quote_ko
    assert results[0].stale is True
    assert results[0].error is None


async def test_get_quotes_provider_error_no_cache(service, provider) -> None:
    provider.failing.add('KO')

    results = await service.get_quotes(['NYSE:KO'])

    assert results[0].quote is None
    assert results[0].error == ERROR_PROVIDER


async def test_get_quotes_not_found_cached(service, provider) -> None:
    await service.get_quotes(['NYSE:NOPE'])

    results = await service.get_quotes(['NYSE:NOPE'])

    assert results[0].error == ERROR_NOT_FOUND
    assert provider.calls == ['NOPE']


async def test_get_quotes_order_and_duplicates(service, provider, quote_ko) -> None:
    provider.quotes['KO'] = quote_ko

    results = await service.get_quotes(['NYSE:NOPE', 'NYSE:KO', 'MOEX:SBER', 'KO'])

    assert [result.query for result in results] == ['NYSE:NOPE', 'NYSE:KO', 'MOEX:SBER', 'KO']
    assert results[0].error == ERROR_NOT_FOUND
    assert results[1].quote == quote_ko
    assert results[2].error == 'unknown exchange MOEX'
    assert results[3].quote == quote_ko
    assert sorted(provider.calls) == ['KO', 'NOPE']


async def test_get_quotes_in_pounds(service, provider) -> None:
    provider.quotes['VOD.L'] = Quote(symbol='VOD.L', currency='GBp', price=116.95)

    results = await service.get_quotes(['LSE:VOD'], in_pounds=True)

    assert results[0].quote.currency == 'GBP'
    assert results[0].quote.price == 1.1695


async def test_get_quotes_single_flight(service, provider, quote_ko) -> None:
    provider.quotes['KO'] = quote_ko

    results = await asyncio.gather(*(service.get_quotes(['NYSE:KO']) for _ in range(10)))

    assert all(result[0].quote == quote_ko for result in results)
    assert provider.calls == ['KO']
