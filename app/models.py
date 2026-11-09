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
    priceopen: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None
    closeyest: float | None = None
    change: float | None = None
    tradetime: datetime | None = None

    def in_pounds(self) -> 'Quote':
        """Convert pence-quoted instrument to GBP."""
        if self.currency not in PENCE_CURRENCIES:
            return self

        def _div(amount: float | None) -> float | None:
            return None if amount is None else round(amount / 100, 8)

        return self.model_copy(update={
            'currency': 'GBP',
            'price': _div(self.price),
            'priceopen': _div(self.priceopen),
            'high': _div(self.high),
            'low': _div(self.low),
            'closeyest': _div(self.closeyest),
            'change': _div(self.change),
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
