"""Tenant DTOs."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateTenantDTO(BaseModel):
    """DTO for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    wa_session: str = Field(..., min_length=1, max_length=100, description="WAHA session name")
    llm_config_name: str = Field(..., description="LLM configuration name")
    agent_prompt: str = Field(..., description="AI agent system prompt")
    payment_provider: str = Field("midtrans", description="Payment provider")
    payment_config: dict[str, Any] = Field(default_factory=dict, description="Payment config")
    business_hours: dict[str, str] = Field(default_factory=dict, description="Business hours")


class UpdateTenantDTO(BaseModel):
    """DTO for updating a tenant."""

    name: str | None = Field(None, min_length=1, max_length=255)
    agent_prompt: str | None = None
    payment_config: dict[str, Any] | None = None
    business_hours: dict[str, str] | None = None
    is_active: bool | None = None


class TenantDTO(BaseModel):
    """DTO for tenant data."""

    id: str
    name: str
    wa_session: str
    llm_config_name: str
    agent_prompt: str
    payment_provider: str
    payment_config: dict[str, Any]
    business_hours: dict[str, str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
