from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "backend/.env.example"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Nuro API"
    environment: Literal["development", "staging", "production", "test"] = "development"
    api_v1_prefix: str = "/api"

    database_url: str = Field(
        default="sqlite+aiosqlite:///./nuro.db", alias="DATABASE_URL"
    )
    test_database_url: str | None = Field(
        default=None, alias="TEST_DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    jwt_secret_key: str = Field(default="changeme", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    rate_limit_tokens: int = Field(default=60, alias="RATE_LIMIT_TOKENS")
    rate_limit_period_seconds: int = Field(default=60, alias="RATE_LIMIT_PERIOD")

    long_poll_timeout_seconds: float = Field(default=30.0, alias="LONG_POLL_TIMEOUT")
    long_poll_interval_seconds: float = Field(default=0.5, alias="LONG_POLL_INTERVAL")

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
