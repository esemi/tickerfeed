"""Google-style symbols (EXCHANGE:TICKER) to provider symbols mapping."""

# exchange prefix -> Yahoo suffix
_EXCHANGE_SUFFIXES: dict[str, str] = {
    'LSE': '.L',
    'LON': '.L',
    'NYSE': '',
    'NASDAQ': '',
    'NYSEARCA': '',
    'NYSEAMERICAN': '',
    'BATS': '',
}


class UnknownExchangeError(ValueError):
    """Exchange prefix is not supported."""


def to_yahoo(symbol: str) -> str:
    """Convert `LSE:VUSA` / `NYSE:KO` / bare `KO` to the Yahoo Finance symbol."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError('empty symbol')

    exchange, sep, ticker = symbol.partition(':')
    if not sep:
        return symbol

    if exchange not in _EXCHANGE_SUFFIXES:
        raise UnknownExchangeError(f'unknown exchange {exchange}')
    if not ticker:
        raise ValueError('empty ticker')
    # Google пишет BRK.B, Yahoo — BRK-B
    return ticker.replace('.', '-') + _EXCHANGE_SUFFIXES[exchange]
