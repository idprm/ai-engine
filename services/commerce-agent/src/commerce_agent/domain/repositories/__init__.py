"""Repository interfaces for Commerce Agent domain."""

from commerce_agent.domain.repositories.tenant_repository import TenantRepository
from commerce_agent.domain.repositories.customer_repository import CustomerRepository
from commerce_agent.domain.repositories.product_repository import ProductRepository
from commerce_agent.domain.repositories.order_repository import OrderRepository
from commerce_agent.domain.repositories.conversation_repository import ConversationRepository
from commerce_agent.domain.repositories.payment_repository import PaymentRepository
from commerce_agent.domain.repositories.label_repository import LabelRepository, ConversationLabelRepository
from commerce_agent.domain.repositories.quick_reply_repository import QuickReplyRepository
from commerce_agent.domain.repositories.ticket_repository import (
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
