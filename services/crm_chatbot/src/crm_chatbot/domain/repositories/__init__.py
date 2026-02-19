"""Repository interfaces for CRM chatbot domain."""

from crm_chatbot.domain.repositories.tenant_repository import TenantRepository
from crm_chatbot.domain.repositories.customer_repository import CustomerRepository
from crm_chatbot.domain.repositories.product_repository import ProductRepository
from crm_chatbot.domain.repositories.order_repository import OrderRepository
from crm_chatbot.domain.repositories.conversation_repository import ConversationRepository
from crm_chatbot.domain.repositories.payment_repository import PaymentRepository
from crm_chatbot.domain.repositories.label_repository import LabelRepository, ConversationLabelRepository
from crm_chatbot.domain.repositories.quick_reply_repository import QuickReplyRepository
from crm_chatbot.domain.repositories.ticket_repository import (
    TicketRepository,
    TicketBoardRepository,
    TicketTemplateRepository,
)

__all__ = [
    "TenantRepository",
    "CustomerRepository",
    "ProductRepository",
    "OrderRepository",
    "ConversationRepository",
    "PaymentRepository",
    "LabelRepository",
    "ConversationLabelRepository",
    "QuickReplyRepository",
    "TicketRepository",
    "TicketBoardRepository",
    "TicketTemplateRepository",
]
