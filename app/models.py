"""Quote models."""
from datetime import datetime

from pydantic import BaseModel

PENCE_CURRENCIES = frozenset(('GBp', 'GBX'))


class Quote(BaseModel):
    """Single instrument quote, GOOGLEFINANCE attribute names."""

    symbol: str
    name: str | None = None
    currency: str | None = None
    price: float | None = None

    def in_pounds(self) -> 'Quote':
        """Convert pence-quoted instrument to GBP."""
        if self.currency not in PENCE_CURRENCIES:
            return self

        return self.model_copy(update={
            'currency': 'GBP',
            'price': None if self.price is None else round(self.price / 100, 8),
        })


class CachedQuote(BaseModel):
    """Cache envelope: quote or not-found marker plus fetch time."""

    fetched_at: datetime
    quote: Quote | None = None


class QuoteResult(BaseModel):
    """API response item, keeps request order."""

    query: str
    quote: Quote | None = None
    stale: bool = False
    error: str | None = None
