from app.models import Quote


def test_in_pounds_pence() -> None:
    quote = Quote(symbol='VOD.L', currency='GBp', price=116.95)

    result = quote.in_pounds()

    assert result.currency == 'GBP'
    assert result.price == 1.1695


def test_in_pounds_not_pence(quote_ko) -> None:
    result = quote_ko.in_pounds()

    assert result == quote_ko
