"""Order DTOs."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OrderItemDTO(BaseModel):
    """DTO for order item."""

    product_id: str
    product_name: str
    variant_sku: str | None
    quantity: int = Field(..., gt=0)
    unit_price: float
    subtotal: float


class CreateOrderDTO(BaseModel):
    """DTO for creating an order."""

    customer_id: str
    items: list[OrderItemDTO] | None = None
    shipping_address: dict[str, Any] | None = None
    notes: str | None = None


class AddOrderItemDTO(BaseModel):
    """DTO for adding item to order."""

    product_id: str
    quantity: int = Field(..., gt=0)
    variant_sku: str | None = None


class OrderDTO(BaseModel):
    """DTO for order data."""

    id: str
    tenant_id: str
    customer_id: str
    items: list[OrderItemDTO]
    status: str
    payment_status: str
    subtotal: float
    shipping_cost: float
    total: float
    currency: str
    shipping_address: dict[str, Any] | None
    payment_id: str | None
    notes: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateOrderStatusDTO(BaseModel):
    """DTO for updating order status."""

    status: str = Field(..., description="New status")
    notes: str | None = Field(None, description="Optional notes")


class ConfirmOrderDTO(BaseModel):
    """DTO for confirming an order."""

    shipping_address: dict[str, Any] | None = Field(None, description="Shipping address")

    class Config:
        json_schema_extra = {
            "example": {
                "shipping_address": {
                    "street": "Jl. Sudirman No. 123",
                    "city": "Jakarta",
                    "province": "DKI Jakarta",
                    "postal_code": "12345",
                    "country": "ID"
                }
            }
        }


class InitiatePaymentDTO(BaseModel):
    """DTO for initiating payment."""

    payment_method: str = Field(
        ...,
        description="Payment method: bank_transfer, ewallet, or qris"
    )
