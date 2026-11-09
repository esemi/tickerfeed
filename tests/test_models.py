from app.models import Quote


def test_in_pounds_pence() -> None:
    quote = Quote(symbol='VOD.L', currency='GBp', price=116.95, priceopen=116.1, high=117.5, low=115.6,
                  closeyest=116.5, change=0.45, volume=100)

    result = quote.in_pounds()

    assert result.currency == 'GBP'
    assert result.price == 1.1695
    assert result.priceopen == 1.161
    assert result.closeyest == 1.165
    assert result.change == 0.0045
    assert result.volume == 100


def test_in_pounds_not_pence(quote_ko) -> None:
    result = quote_ko.in_pounds()

    assert result == quote_ko
