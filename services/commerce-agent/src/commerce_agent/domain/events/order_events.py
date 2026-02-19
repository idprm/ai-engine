"""Order domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent
from commerce_agent.domain.value_objects import OrderId, TenantId, CustomerId, ProductId, OrderStatus


@dataclass
class OrderCreated(DomainEvent):
    """Event emitted when a new order is created."""
    order_id: OrderId = None
    tenant_id: TenantId = None
    customer_id: CustomerId = None
    event_type: str = "order.created"


@dataclass
class OrderStatusChanged(DomainEvent):
    """Event emitted when an order's status changes."""
    order_id: OrderId = None
    old_status: OrderStatus = None
    new_status: OrderStatus = None
    event_type: str = "order.status_changed"


@dataclass
class OrderItemAdded(DomainEvent):
    """Event emitted when an item is added to an order."""
    order_id: OrderId = None
    product_id: ProductId = None
    quantity: int = 0
    event_type: str = "order.item_added"
