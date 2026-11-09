"""Quote provider interface."""
from typing import Protocol

from app.models import Quote


class SymbolNotFoundError(LookupError):
    """Provider knows nothing about the symbol."""


class ProviderError(RuntimeError):
    """Provider is unavailable or returned garbage."""


class QuoteProvider(Protocol):
    """Fetches a fresh quote for a single provider symbol."""

    async def fetch(self, symbol: str) -> Quote:
        """Return quote or raise SymbolNotFoundError / ProviderError."""
        ...
