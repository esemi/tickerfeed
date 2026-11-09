"""HTTP API for the Google Sheets add-on."""
import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from redis.asyncio import Redis

from app.cache import QuoteCache
from app.models import QuoteResult
from app.providers.yahoo import YahooProvider
from app.service import CacheTtl, QuoteService
from app.settings import app_settings


class QuotesResponse(BaseModel):
    """Quotes endpoint response."""

    results: list[QuoteResult]


def build_service(redis: Redis, client: httpx.AsyncClient) -> QuoteService:
    """Wire service dependencies."""
    return QuoteService(
        provider=YahooProvider(client, concurrency=app_settings.provider_concurrency),
        cache=QuoteCache(redis),
        ttl=CacheTtl(
            fresh=app_settings.cache_fresh_ttl,
            stale=app_settings.cache_stale_ttl,
            not_found=app_settings.cache_not_found_ttl,
        ),
    )


def build_http_client() -> httpx.AsyncClient:
    """HTTP client for quote providers."""
    return httpx.AsyncClient(
        timeout=app_settings.http_timeout,
        headers={'User-Agent': app_settings.http_user_agent},
        proxy=app_settings.http_proxy,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open shared redis & http connections."""
    redis = Redis.from_url(app_settings.redis_dsn)
    async with build_http_client() as client:
        app.state.service = build_service(redis, client)
        yield
    await redis.aclose()


app = FastAPI(title='tickerfeed', lifespan=lifespan, docs_url=None, redoc_url=None)


def check_api_key(x_api_key: Annotated[str, Header()] = '') -> None:
    """Reject requests without a valid shared secret."""
    if not secrets.compare_digest(x_api_key, app_settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid api key')


@app.get('/health')
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {'status': 'ok'}


@app.get('/v1/quotes', dependencies=[Depends(check_api_key)])
async def quotes(
    request: Request,
    symbols: Annotated[str, Query(description='Comma separated, e.g. LSE:VUSA,NYSE:KO')],
    gbp: Annotated[bool, Query(description='Convert pence-quoted LSE instruments to GBP')] = False,
) -> QuotesResponse:
    """Quotes for the requested symbols, same order as requested."""
    queries = [symbol.strip() for symbol in symbols.split(',') if symbol.strip()]
    if not queries:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail='no symbols')
    if len(queries) > app_settings.max_symbols_per_request:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail='too many symbols')

    service: QuoteService = request.app.state.service
    return QuotesResponse(results=await service.get_quotes(queries, in_pounds=gbp))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=app_settings.host, port=app_settings.port, proxy_headers=False)
