"""Domain events for Commerce Agent bounded context."""

from shared.events import DomainEvent

# Re-export base DomainEvent
__all__ = ["DomainEvent"]

# Import specific events
from commerce_agent.domain.events.tenant_events import TenantCreated, TenantUpdated
from commerce_agent.domain.events.customer_events import CustomerCreated, CustomerUpdated
from commerce_agent.domain.events.product_events import ProductCreated
from commerce_agent.domain.events.order_events import (
    OrderCreated,
    OrderStatusChanged,
    OrderItemAdded,
)
from commerce_agent.domain.events.conversation_events import (
    ConversationCreated,
    ConversationMessageAdded,
    ConversationStateChanged,
)
from commerce_agent.domain.events.payment_events import (
    PaymentInitiated,
    PaymentStatusChanged,
)
from commerce_agent.domain.events.label_events import (
    LabelCreated,
    LabelUpdated,
    LabelDeleted,
    ConversationLabeled,
    ConversationUnlabeled,
)
from commerce_agent.domain.events.ticket_events import (
    TicketCreated,
    TicketStatusChanged,
    TicketPriorityChanged,
    TicketAssigned,
    TicketResolved,
    TicketClosed,
    TicketReopened,
)

__all__ = [
    "DomainEvent",
    "TenantCreated",
    "TenantUpdated",
    "CustomerCreated",
    "CustomerUpdated",
    "ProductCreated",
    "OrderCreated",
    "OrderStatusChanged",
    "OrderItemAdded",
    "ConversationCreated",
    "ConversationMessageAdded",
    "ConversationStateChanged",
    "PaymentInitiated",
    "PaymentStatusChanged",
    "LabelCreated",
    "LabelUpdated",
    "LabelDeleted",
    "ConversationLabeled",
    "ConversationUnlabeled",
    "TicketCreated",
    "TicketStatusChanged",
    "TicketPriorityChanged",
    "TicketAssigned",
    "TicketResolved",
    "TicketClosed",
    "TicketReopened",
]
