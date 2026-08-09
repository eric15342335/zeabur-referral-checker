"""Environment-backed runtime settings."""

from typing import Any, cast

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from REFCHECK-prefixed variables."""

    model_config = SettingsConfigDict(
        env_prefix="REFCHECK_", env_file=".env", extra="forbid"
    )

    endpoint: AnyHttpUrl = AnyHttpUrl("https://api-bunny.zeabur.com/graphql")
    origin: AnyHttpUrl = AnyHttpUrl("https://zeabur.com")
    locale: str = "en-US"
    order_type: str = "RENT_SERVER"
    cookie: SecretStr
    concurrency: int = Field(default=8, ge=1, le=64)
    requests_per_second: float = Field(default=4.0, gt=0, le=50)
    timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    retries: int = Field(default=3, ge=1, le=10)

    @field_validator("cookie")
    @classmethod
    def cookie_must_not_be_blank(cls, value: SecretStr) -> SecretStr:
        """Require a usable authorized session cookie."""
        if not value.get_secret_value().strip():
            raise ValueError("must be a non-empty Cookie header value")
        return value


def load_settings(**overrides: object) -> Settings:
    """Load settings from the environment and optional runtime overrides."""
    return Settings(**cast(dict[str, Any], overrides))
