"""Product DTOs."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProductVariantDTO(BaseModel):
    """DTO for product variant."""

    sku: str = Field(..., description="Variant SKU")
    name: str = Field(..., description="Variant name")
    price: float = Field(..., ge=0, description="Price in major currency unit")
    stock: int = Field(default=0, ge=0, description="Stock quantity")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Variant attributes")


class CreateProductDTO(BaseModel):
    """DTO for creating a product."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, description="Product description")
    category: str | None = Field(None, max_length=100)
    base_price: float = Field(..., ge=0, description="Base price in major currency unit")
    variants: list[ProductVariantDTO] = Field(default_factory=list)


class ProductDTO(BaseModel):
    """DTO for product data."""

    id: str
    tenant_id: str
    name: str
    description: str | None
    category: str | None
    base_price: float
    currency: str
    is_active: bool
    variants: list[ProductVariantDTO]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateProductVariantDTO(BaseModel):
    """DTO for adding a variant to existing product."""

    sku: str = Field(..., description="Variant SKU")
    name: str = Field(..., description="Variant name")
    price: float = Field(..., ge=0)
    stock: int = Field(default=0, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
