"""Product and ProductVariant entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from commerce_agent.domain.events import ProductCreated, DomainEvent
from commerce_agent.domain.value_objects import ProductId, TenantId, Money


@dataclass
class ProductVariant:
    """Product variant entity representing a specific SKU.

    Variants have different attributes (size, color, etc.) and pricing.
    """

    _sku: str
    _name: str
    _price: Money
    _stock: int
    _attributes: dict  # {"size": "L", "color": "red"}
    _id: int | None = None

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def name(self) -> str:
        return self._name

    @property
    def price(self) -> Money:
        return self._price

    @property
    def stock(self) -> int:
        return self._stock

    @property
    def attributes(self) -> dict:
        return self._attributes.copy()

    @classmethod
    def create(
        cls,
        sku: str,
        name: str,
        price: Money,
        stock: int = 0,
        attributes: dict | None = None,
        variant_id: int | None = None,
    ) -> "ProductVariant":
        """Factory method to create a ProductVariant."""
        return cls(
            _id=variant_id,
            _sku=sku,
            _name=name,
            _price=price,
            _stock=stock,
            _attributes=attributes or {},
        )

    def update_stock(self, quantity: int) -> None:
        """Update stock level (absolute value)."""
        if quantity < 0:
            raise ValueError("Stock cannot be negative")
        self._stock = quantity

    def decrease_stock(self, quantity: int) -> None:
        """Decrease stock by quantity."""
        if quantity > self._stock:
            raise ValueError(f"Insufficient stock: have {self._stock}, need {quantity}")
        self._stock -= quantity

    def increase_stock(self, quantity: int) -> None:
        """Increase stock by quantity."""
        self._stock += quantity

    def is_available(self, quantity: int = 1) -> bool:
        """Check if variant is available in requested quantity."""
        return self._stock >= quantity and self._stock > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert variant to dictionary representation."""
        return {
            "id": self._id,
            "sku": self._sku,
            "name": self._name,
            "price": self._price.to_float(),
            "stock": self._stock,
            "attributes": self._attributes,
        }


@dataclass
class Product:
    """Product aggregate root representing a catalog item.

    Products belong to a tenant and can have multiple variants (SKUs).
    """

    _id: ProductId
    _tenant_id: TenantId
    _name: str
    _description: str
    _category: str | None
    _base_price: Money
    _is_active: bool = True
    _variants: list[ProductVariant] = field(default_factory=list)
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit ProductCreated event for new products."""
        if not self._events:
            self._add_event(ProductCreated(
                product_id=self._id,
                tenant_id=self._tenant_id,
                name=self._name,
            ))

    @property
    def id(self) -> ProductId:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def category(self) -> str | None:
        return self._category

    @property
    def base_price(self) -> Money:
        return self._base_price

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def variants(self) -> list[ProductVariant]:
        return self._variants.copy()

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        description: str,
        base_price: Money,
        category: str | None = None,
        product_id: ProductId | None = None,
    ) -> "Product":
        """Factory method to create a new Product."""
        return cls(
            _id=product_id or ProductId.generate(),
            _tenant_id=tenant_id,
            _name=name,
            _description=description,
            _category=category,
            _base_price=base_price,
        )

    def add_variant(self, variant: ProductVariant) -> None:
        """Add a variant to the product."""
        # Check for duplicate SKU
        if any(v.sku == variant.sku for v in self._variants):
            raise ValueError(f"Variant with SKU {variant.sku} already exists")
        self._variants.append(variant)
        self._updated_at = datetime.utcnow()

    def remove_variant(self, sku: str) -> None:
        """Remove a variant by SKU."""
        self._variants = [v for v in self._variants if v.sku != sku]
        self._updated_at = datetime.utcnow()

    def get_variant(self, sku: str) -> ProductVariant | None:
        """Get a variant by SKU."""
        for variant in self._variants:
            if variant.sku == sku:
                return variant
        return None

    def get_available_variants(self) -> list[ProductVariant]:
        """Get all variants with stock > 0."""
        return [v for v in self._variants if v.stock > 0]

    def update_info(
        self,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
    ) -> None:
        """Update product information."""
        if name is not None:
            self._name = name
        if description is not None:
            self._description = description
        if category is not None:
            self._category = category
        self._updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the product."""
        self._is_active = True
        self._updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the product."""
        self._is_active = False
        self._updated_at = datetime.utcnow()

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert product to dictionary representation."""
        return {
            "id": str(self._id),
            "tenant_id": str(self._tenant_id),
            "name": self._name,
            "description": self._description,
            "category": self._category,
            "base_price": self._base_price.to_float(),
            "is_active": self._is_active,
            "variants": [v.to_dict() for v in self._variants],
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
