"""Domain entities for CRM chatbot."""

from crm_chatbot.domain.entities.tenant import Tenant
from crm_chatbot.domain.entities.customer import Customer
from crm_chatbot.domain.entities.product import Product, ProductVariant
from crm_chatbot.domain.entities.order import Order, OrderItem
from crm_chatbot.domain.entities.conversation import Conversation, ConversationMessage
from crm_chatbot.domain.entities.payment import Payment

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
]
