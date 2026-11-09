"""Redis-backed quotes cache."""
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.models import CachedQuote

KEY_PREFIX = 'tickerfeed:quote:'


class QuoteCache:
    """Stores quote envelopes; freshness is decided by the caller via fetched_at."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_many(self, symbols: list[str]) -> dict[str, CachedQuote]:
        """Return cached envelopes for known symbols."""
        if not symbols:
            return {}
        raw_values = await self._redis.mget([KEY_PREFIX + symbol for symbol in symbols])
        return {
            symbol: CachedQuote.model_validate_json(raw)
            for symbol, raw in zip(symbols, raw_values, strict=True)
            if raw is not None
        }

    async def put(self, symbol: str, entry: CachedQuote, ttl: int) -> None:
        """Save envelope with the given TTL."""
        await self._redis.set(KEY_PREFIX + symbol, entry.model_dump_json(), ex=ttl)


def utcnow() -> datetime:
    """Current UTC time (patchable in tests)."""
    return datetime.now(tz=UTC)
