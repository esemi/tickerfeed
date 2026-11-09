import pytest

from app.symbols import UnknownExchangeError, to_yahoo


@pytest.mark.parametrize(('symbol', 'expected'), [
    ('LSE:VUSA', 'VUSA.L'),
    ('LON:vod', 'VOD.L'),
    ('NYSE:KO', 'KO'),
    ('NASDAQ:AAPL', 'AAPL'),
    ('NYSE:BRK.B', 'BRK-B'),
    (' KO ', 'KO'),
    ('VUSA.L', 'VUSA.L'),
])
def test_to_yahoo(symbol: str, expected: str) -> None:
    result = to_yahoo(symbol)

    assert result == expected


def test_to_yahoo_unknown_exchange() -> None:
    with pytest.raises(UnknownExchangeError):
        to_yahoo('MOEX:SBER')


@pytest.mark.parametrize('symbol', ['', '  ', 'LSE:'])
def test_to_yahoo_empty(symbol: str) -> None:
    with pytest.raises(ValueError, match='empty'):
        to_yahoo(symbol)
