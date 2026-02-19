"""Domain entities for CRM chatbot."""

from crm_chatbot.domain.entities.tenant import Tenant
from crm_chatbot.domain.entities.customer import Customer
from crm_chatbot.domain.entities.product import Product, ProductVariant
from crm_chatbot.domain.entities.order import Order, OrderItem
from crm_chatbot.domain.entities.conversation import Conversation, ConversationMessage
from crm_chatbot.domain.entities.payment import Payment
from crm_chatbot.domain.entities.label import Label, ConversationLabel
from crm_chatbot.domain.entities.quick_reply import QuickReply
from crm_chatbot.domain.entities.ticket import Ticket, TicketBoard, TicketTemplate

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
