"""Customer DTOs."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, EmailStr


class CustomerDTO(BaseModel):
    """DTO for customer data."""

    id: str
    tenant_id: str
    phone_number: str
    wa_chat_id: str
    name: str | None
    email: str | None
    address: dict[str, Any] | None
    tags: list[str]
    total_orders: int
    total_spent: float
    is_vip: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateCustomerDTO(BaseModel):
    """DTO for updating customer profile."""

    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    address: dict[str, Any] | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "address": {
                    "street": "Jl. Sudirman No. 123",
                    "city": "Jakarta",
                    "province": "DKI Jakarta",
                    "postal_code": "12345",
                    "country": "ID"
                }
            }
        }


class AddCustomerTagDTO(BaseModel):
    """DTO for adding a tag to customer."""

    tag: str = Field(..., min_length=1, max_length=50)


class CreateCustomerDTO(BaseModel):
    """DTO for manually creating a customer."""

    phone_number: str = Field(..., description="Phone number")
    name: str | None = None
    email: EmailStr | None = None
    address: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
