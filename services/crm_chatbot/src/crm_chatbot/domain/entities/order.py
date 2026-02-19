"""Order and OrderItem entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from crm_chatbot.domain.events import (
    OrderCreated,
    OrderStatusChanged,
    OrderItemAdded,
    DomainEvent,
)
from crm_chatbot.domain.value_objects import (
    OrderId,
    TenantId,
    CustomerId,
    ProductId,
    Money,
    OrderStatus,
    PaymentStatus,
)


@dataclass
class OrderItem:
    """Order item entity representing a line item in an order."""

    _product_id: ProductId
    _product_name: str
    _variant_sku: str | None
    _quantity: int
    _unit_price: Money
    _subtotal: Money
    _id: int | None = None

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def product_id(self) -> ProductId:
        return self._product_id

    @property
    def product_name(self) -> str:
        return self._product_name

    @property
    def variant_sku(self) -> str | None:
        return self._variant_sku

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def unit_price(self) -> Money:
        return self._unit_price

    @property
    def subtotal(self) -> Money:
        return self._subtotal

    @classmethod
    def create(
        cls,
        product_id: ProductId,
        product_name: str,
        quantity: int,
        unit_price: Money,
        variant_sku: str | None = None,
        item_id: int | None = None,
    ) -> "OrderItem":
        """Factory method to create an OrderItem."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        subtotal = unit_price * quantity
        return cls(
            _id=item_id,
            _product_id=product_id,
            _product_name=product_name,
            _variant_sku=variant_sku,
            _quantity=quantity,
            _unit_price=unit_price,
            _subtotal=subtotal,
        )

    def update_quantity(self, quantity: int) -> None:
        """Update quantity and recalculate subtotal."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self._quantity = quantity
        self._subtotal = self._unit_price * quantity

    def to_dict(self) -> dict[str, Any]:
        """Convert item to dictionary representation."""
        return {
            "id": self._id,
            "product_id": str(self._product_id),
            "product_name": self._product_name,
            "variant_sku": self._variant_sku,
            "quantity": self._quantity,
            "unit_price": self._unit_price.to_float(),
            "subtotal": self._subtotal.to_float(),
        }


@dataclass
class Order:
    """Order aggregate root representing a transaction.

    Orders go through status transitions:
    PENDING -> CONFIRMED -> PROCESSING -> SHIPPED -> DELIVERED
                    |              |
                    v              v
                CANCELLED      CANCELLED
    """

    _id: OrderId
    _tenant_id: TenantId
    _customer_id: CustomerId
    _items: list[OrderItem]
    _status: OrderStatus = OrderStatus.PENDING
    _payment_status: PaymentStatus = PaymentStatus.PENDING
    _subtotal: Money = field(default_factory=lambda: Money(amount=0))
    _shipping_cost: Money = field(default_factory=lambda: Money(amount=0))
    _total: Money = field(default_factory=lambda: Money(amount=0))
    _shipping_address: dict | None = None
    _payment_id: str | None = None
    _notes: str | None = None
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit OrderCreated event for new orders."""
        self._recalculate_totals()
        if not self._events:
            self._add_event(OrderCreated(
                order_id=self._id,
                tenant_id=self._tenant_id,
                customer_id=self._customer_id,
            ))

    @property
    def id(self) -> OrderId:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def customer_id(self) -> CustomerId:
        return self._customer_id

    @property
    def items(self) -> list[OrderItem]:
        return self._items.copy()

    @property
    def status(self) -> OrderStatus:
        return self._status

    @property
    def payment_status(self) -> PaymentStatus:
        return self._payment_status

    @property
    def subtotal(self) -> Money:
        return self._subtotal

    @property
    def shipping_cost(self) -> Money:
        return self._shipping_cost

    @property
    def total(self) -> Money:
        return self._total

    @property
    def shipping_address(self) -> dict | None:
        return self._shipping_address.copy() if self._shipping_address else None

    @property
    def payment_id(self) -> str | None:
        return self._payment_id

    @property
    def notes(self) -> str | None:
        return self._notes

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def item_count(self) -> int:
        """Total number of items in the order."""
        return sum(item.quantity for item in self._items)

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        customer_id: CustomerId,
        items: list[OrderItem] | None = None,
        shipping_address: dict | None = None,
        notes: str | None = None,
        order_id: OrderId | None = None,
    ) -> "Order":
        """Factory method to create a new Order."""
        return cls(
            _id=order_id or OrderId.generate(),
            _tenant_id=tenant_id,
            _customer_id=customer_id,
            _items=items or [],
            _shipping_address=shipping_address,
            _notes=notes,
        )

    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order."""
        if self._status != OrderStatus.PENDING:
            raise ValueError(f"Cannot add items to order in {self._status} status")

        # Check if product already in order
        for existing_item in self._items:
            if (existing_item.product_id == item.product_id and
                existing_item.variant_sku == item.variant_sku):
                # Update quantity instead
                existing_item.update_quantity(existing_item.quantity + item.quantity)
                self._recalculate_totals()
                return

        self._items.append(item)
        self._recalculate_totals()
        self._updated_at = datetime.utcnow()
        self._add_event(OrderItemAdded(
            order_id=self._id,
            product_id=item.product_id,
            quantity=item.quantity,
        ))

    def remove_item(self, product_id: ProductId, variant_sku: str | None = None) -> None:
        """Remove an item from the order."""
        if self._status != OrderStatus.PENDING:
            raise ValueError(f"Cannot remove items from order in {self._status} status")

        self._items = [
            item for item in self._items
            if not (item.product_id == product_id and item.variant_sku == variant_sku)
        ]
        self._recalculate_totals()
        self._updated_at = datetime.utcnow()

    def set_shipping_address(self, address: dict) -> None:
        """Set the shipping address."""
        self._shipping_address = address
        self._updated_at = datetime.utcnow()

    def set_shipping_cost(self, cost: Money) -> None:
        """Set the shipping cost."""
        self._shipping_cost = cost
        self._recalculate_totals()
        self._updated_at = datetime.utcnow()

    def confirm(self) -> None:
        """Transition order to CONFIRMED status."""
        if not self._status.can_transition_to(OrderStatus.CONFIRMED):
            raise ValueError(f"Cannot confirm order in {self._status} status")
        if not self._items:
            raise ValueError("Cannot confirm empty order")

        old_status = self._status
        self._status = OrderStatus.CONFIRMED
        self._payment_status = PaymentStatus.PENDING_PAYMENT
        self._updated_at = datetime.utcnow()
        self._add_event(OrderStatusChanged(
            order_id=self._id,
            old_status=old_status,
            new_status=OrderStatus.CONFIRMED,
        ))

    def start_processing(self) -> None:
        """Transition order to PROCESSING status."""
        if not self._status.can_transition_to(OrderStatus.PROCESSING):
            raise ValueError(f"Cannot process order in {self._status} status")

        old_status = self._status
        self._status = OrderStatus.PROCESSING
        self._updated_at = datetime.utcnow()
        self._add_event(OrderStatusChanged(
            order_id=self._id,
            old_status=old_status,
            new_status=OrderStatus.PROCESSING,
        ))

    def ship(self) -> None:
        """Transition order to SHIPPED status."""
        if not self._status.can_transition_to(OrderStatus.SHIPPED):
            raise ValueError(f"Cannot ship order in {self._status} status")

        old_status = self._status
        self._status = OrderStatus.SHIPPED
        self._updated_at = datetime.utcnow()
        self._add_event(OrderStatusChanged(
            order_id=self._id,
            old_status=old_status,
            new_status=OrderStatus.SHIPPED,
        ))

    def deliver(self) -> None:
        """Transition order to DELIVERED status."""
        if not self._status.can_transition_to(OrderStatus.DELIVERED):
            raise ValueError(f"Cannot deliver order in {self._status} status")

        old_status = self._status
        self._status = OrderStatus.DELIVERED
        self._updated_at = datetime.utcnow()
        self._add_event(OrderStatusChanged(
            order_id=self._id,
            old_status=old_status,
            new_status=OrderStatus.DELIVERED,
        ))

    def cancel(self, reason: str | None = None) -> None:
        """Cancel the order."""
        if not self._status.can_transition_to(OrderStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order in {self._status} status")

        old_status = self._status
        self._status = OrderStatus.CANCELLED
        self._payment_status = PaymentStatus.CANCELLED
        self._notes = f"Cancelled: {reason}" if reason else "Cancelled"
        self._updated_at = datetime.utcnow()
        self._add_event(OrderStatusChanged(
            order_id=self._id,
            old_status=old_status,
            new_status=OrderStatus.CANCELLED,
        ))

    def set_payment_id(self, payment_id: str) -> None:
        """Set the payment ID from payment gateway."""
        self._payment_id = payment_id
        self._updated_at = datetime.utcnow()

    def mark_payment_paid(self) -> None:
        """Mark the payment as completed."""
        if self._payment_status.can_transition_to(PaymentStatus.PAID):
            self._payment_status = PaymentStatus.PAID
            self._updated_at = datetime.utcnow()

    def mark_payment_failed(self) -> None:
        """Mark the payment as failed."""
        if self._payment_status.can_transition_to(PaymentStatus.FAILED):
            self._payment_status = PaymentStatus.FAILED
            self._updated_at = datetime.utcnow()

    def _recalculate_totals(self) -> None:
        """Recalculate subtotal and total."""
        self._subtotal = Money(amount=0)
        for item in self._items:
            self._subtotal = self._subtotal + item.subtotal
        self._total = self._subtotal + self._shipping_cost

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert order to dictionary representation."""
        return {
            "id": str(self._id),
            "tenant_id": str(self._tenant_id),
            "customer_id": str(self._customer_id),
            "items": [item.to_dict() for item in self._items],
            "status": self._status.value,
            "payment_status": self._payment_status.value,
            "subtotal": self._subtotal.to_float(),
            "shipping_cost": self._shipping_cost.to_float(),
            "total": self._total.to_float(),
            "shipping_address": self._shipping_address,
            "payment_id": self._payment_id,
            "notes": self._notes,
            "item_count": self.item_count,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
