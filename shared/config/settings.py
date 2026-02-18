"""Pydantic settings management for AI Platform services."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ai-platform"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_job_ttl: int = 3600  # 1 hour TTL for job results

    # RabbitMQ
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/")
    rabbitmq_task_queue: str = "ai_tasks"
    rabbitmq_event_exchange: str = "ai_events"

    # LLM Provider API Keys (env var names, not actual keys)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Service-specific
    service_name: str = "unknown"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if "+asyncpg" not in v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

"""Example usage:"""
# from shared.config.settings import get_settings