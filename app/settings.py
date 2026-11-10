"""Application settings."""
import os

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application settings class."""

    api_key: str = Field(description='Shared secret expected in X-Api-Key header')
    host: str = Field('0.0.0.0')  # noqa: S104
    port: int = Field(8742)
    redis_dsn: str = Field('redis://localhost:6379/4')
    cache_fresh_ttl: int = Field(60 * 15, description='Seconds a quote is considered fresh')
    cache_stale_ttl: int = Field(60 * 60 * 24, description='Seconds a stale quote is kept as a fallback')
    cache_not_found_ttl: int = Field(60 * 60, description='Seconds an unknown symbol is remembered')
    http_timeout: float = Field(10.0)
    http_proxy: str | None = Field(None, description='Scraper proxy, e.g. http://user:pass@host:3128 or socks5://host:1080')
    http_user_agent: str = Field('tickerfeed/0.1')
    provider_concurrency: int = Field(2, description='Max parallel requests to the quotes provider')
    max_symbols_per_request: int = Field(200)


app_settings = AppSettings(
    _env_file=os.path.join(os.path.dirname(__file__), '..', '.env'),  # type:ignore
)
