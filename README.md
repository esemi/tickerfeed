# tickerfeed

Аналог `GOOGLEFINANCE` для Google Sheets, знающий тикеры LSE/NYSE/NASDAQ, которых нет у Google.
Котировки тянутся из Yahoo Finance по запросу и кешируются в Redis на 15 минут.

```
Google Sheets ── Apps Script =TICKERFEED() ──► tickerfeed API ──► Redis (15m fresh / 24h stale)
                                                     └──► Yahoo Finance v8/chart
```

## Использование в таблице

```
=TICKERFEED("LON:CSPX")                 цена
=TICKERFEED("NYSEARCA:VTI"; "closeyest")
=TICKERFEED(A2:A20; "price")            весь диапазон одним запросом
=TICKERFEED("LSE:VOD"; "price"; TRUE)   пенсы → фунты
```

Атрибуты: `price, priceopen, high, low, volume, closeyest, change, currency, name, tradetime`.

Биржи: `LSE`/`LON` → `.L`, `NYSE`, `NYSEARCA`, `NYSEAMERICAN`, `NASDAQ`, `BATS`. Без префикса символ уходит в Yahoo как есть.

Тикеры LSE часто котируются в пенсах (`currency = GBp`). По умолчанию отдаётся как есть, как у GOOGLEFINANCE.

## API

`GET /v1/quotes?symbols=LON:CSPX,NYSEARCA:VTI&gbp=false`, заголовок `X-Api-Key`.
Ответ — список в порядке запроса: `{"results": [{"query", "quote", "stale", "error"}]}`.
`stale=true` — провайдер недоступен, отдана последняя известная котировка (до 24ч).

## Разработка

```shell
poetry install
cp .env.example .env
poetry run python -m app.api
poetry run pytest --cov=app
poetry run ruff check app tests && poetry run mypy app && poetry run vulture app
```

Прокси для скрапера — `http_proxy` в `.env` (`http://`, `https://`, `socks5://`).

## Деплой

- systemd-юнит: `etc/tickerfeed.service`, сервис слушает `port` из `.env` напрямую, без nginx.
- GitHub Actions деплоит master после зелёных тестов. Секреты: `SSH_HOST`, `SSH_USERNAME`, `SSH_PASSWORD`, `TICKERFEED_API_KEY`, `TICKERFEED_PORT`.
- Пользователю `tickerfeed` нужен sudo только на `systemctl restart tickerfeed`.

## Плагин

`gas/` — проект Apps Script (`clasp push` или копипаст в Extensions → Apps Script таблицы).
В Script properties задать `TICKERFEED_URL` и `TICKERFEED_API_KEY`.
