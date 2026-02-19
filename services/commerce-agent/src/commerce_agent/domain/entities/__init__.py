"""Domain entities for CRM chatbot."""

from commerce_agent.domain.entities.tenant import Tenant
from commerce_agent.domain.entities.customer import Customer
from commerce_agent.domain.entities.product import Product, ProductVariant
from commerce_agent.domain.entities.order import Order, OrderItem
from commerce_agent.domain.entities.conversation import Conversation, ConversationMessage
from commerce_agent.domain.entities.payment import Payment
from commerce_agent.domain.entities.label import Label, ConversationLabel
from commerce_agent.domain.entities.quick_reply import QuickReply
from commerce_agent.domain.entities.ticket import Ticket, TicketBoard, TicketTemplate

__all__ = [
    "Tenant",
    "Customer",
    "Product",
    "ProductVariant",
    "Order",
    "OrderItem",
    "Conversation",
    "ConversationMessage",
    "Payment",
    "Label",
    "ConversationLabel",
    "QuickReply",
    "Ticket",
    "TicketBoard",
    "TicketTemplate",
]
