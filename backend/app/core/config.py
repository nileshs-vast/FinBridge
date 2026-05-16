from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-production-please"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://finbridge:finbridge@localhost:5432/finbridge"
    )

    JWT_SECRET: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    @model_validator(mode="after")
    def _reject_default_secret_in_production(self) -> "Settings":
        if self.APP_ENV == "production" and self.JWT_SECRET == _DEFAULT_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong secret in production")
        return self

    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    EXTRACTION_PROVIDER: Literal["fixture", "claude", "gemini"] = "fixture"
    FIXTURE_SEEDS_DIR: str = "seeds/extractions"
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
