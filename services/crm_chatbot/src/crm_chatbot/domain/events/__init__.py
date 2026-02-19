"""Domain events for CRM chatbot bounded context."""

from shared.events import DomainEvent

# Re-export base DomainEvent
__all__ = ["DomainEvent"]

# Import specific events
from crm_chatbot.domain.events.tenant_events import TenantCreated, TenantUpdated
from crm_chatbot.domain.events.customer_events import CustomerCreated, CustomerUpdated
from crm_chatbot.domain.events.product_events import ProductCreated
from crm_chatbot.domain.events.order_events import (
    OrderCreated,
    OrderStatusChanged,
    OrderItemAdded,
)
from crm_chatbot.domain.events.conversation_events import (
    ConversationCreated,
    ConversationMessageAdded,
    ConversationStateChanged,
)
from crm_chatbot.domain.events.payment_events import (
    PaymentInitiated,
    PaymentStatusChanged,
)
from crm_chatbot.domain.events.label_events import (
    LabelCreated,
    LabelUpdated,
    LabelDeleted,
    ConversationLabeled,
    ConversationUnlabeled,
)
from crm_chatbot.domain.events.ticket_events import (
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
