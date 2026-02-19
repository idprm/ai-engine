"""Payment domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent
from commerce_agent.domain.value_objects import OrderId, Money, PaymentStatus


@dataclass
class PaymentInitiated(DomainEvent):
    """Event emitted when a payment is initiated."""
    payment_id: str = ""
    order_id: OrderId = None
    amount: Money = None
    event_type: str = "payment.initiated"


@dataclass
class PaymentStatusChanged(DomainEvent):
    """Event emitted when a payment's status changes."""
    payment_id: str = ""
    old_status: PaymentStatus = None
    new_status: PaymentStatus = None
    event_type: str = "payment.status_changed"
