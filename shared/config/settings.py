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
    rabbitmq_wa_queue: str = "wa_messages"  # Queue for WhatsApp outgoing messages
    rabbitmq_crm_queue: str = "crm_tasks"  # Queue for CRM processing tasks

    # Midtrans Payment Gateway
    midtrans_server_key: str = ""
    midtrans_client_key: str = ""
    midtrans_is_production: bool = False

    # Xendit Payment Gateway (optional)
    xendit_secret_key: str = ""

    # Message Buffer Settings (for CRM chatbot)
    message_buffer_initial_delay: float = 2.0
    message_buffer_max_delay: float = 10.0
    buffer_flush_interval: float = 0.5

    # LLM Provider API Keys (env var names, not actual keys)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # LLM Resilience Settings
    llm_default_timeout_seconds: int = 120  # Default timeout for LLM calls
    llm_max_retries: int = 3  # Max retries for LLM calls
    llm_retry_initial_delay: float = 1.0  # Initial delay before first retry
    llm_retry_max_delay: float = 60.0  # Maximum delay between retries
    llm_retry_multiplier: float = 2.0  # Exponential backoff multiplier

    # Circuit Breaker Settings
    circuit_breaker_failure_threshold: int = 5  # Failures before opening circuit
    circuit_breaker_success_threshold: int = 2  # Successes in half-open to close
    circuit_breaker_timeout_seconds: float = 60.0  # Time before attempting half-open

    # Job Retry Settings
    job_default_max_retries: int = 3  # Default max retries for failed jobs
    job_retry_delay_min: float = 5.0  # Minimum delay before job retry
    job_retry_delay_max: float = 300.0  # Maximum delay before job retry

    # WAHA (WhatsApp HTTP API) Configuration
    waha_server_url: str = Field(default="http://localhost:3000")
    waha_api_key: str | None = None
    waha_webhook_secret: str | None = None  # HMAC secret for webhook validation
    waha_session: str = "default"

    # Google Geocoding API (for reverse geocoding WhatsApp locations)
    google_geocoding_api_key: str | None = None  # Required for reverse geocoding
    google_geocoding_base_url: str = "https://maps.googleapis.com/maps/api/geocode/json"

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