"""Value objects for CRM chatbot domain."""

from commerce_agent.domain.value_objects.tenant_id import TenantId
from commerce_agent.domain.value_objects.customer_id import CustomerId
from commerce_agent.domain.value_objects.product_id import ProductId
from commerce_agent.domain.value_objects.order_id import OrderId
from commerce_agent.domain.value_objects.order_status import OrderStatus, PaymentStatus
from commerce_agent.domain.value_objects.money import Money
from commerce_agent.domain.value_objects.conversation_state import ConversationState
from commerce_agent.domain.value_objects.phone_number import PhoneNumber
from commerce_agent.domain.value_objects.wa_chat_id import WAChatId
from commerce_agent.domain.value_objects.label_id import LabelId
from commerce_agent.domain.value_objects.quick_reply_id import QuickReplyId
from commerce_agent.domain.value_objects.ticket_id import TicketId
from commerce_agent.domain.value_objects.ticket_status import TicketStatus, TicketState
from commerce_agent.domain.value_objects.ticket_priority import TicketPriority, PriorityLevel

__all__ = [
    "TenantId",
    "CustomerId",
    "ProductId",
    "OrderId",
    "OrderStatus",
    "PaymentStatus",
    "Money",
    "ConversationState",
    "PhoneNumber",
    "WAChatId",
    "LabelId",
    "QuickReplyId",
    "TicketId",
    "TicketStatus",
    "TicketState",
    "TicketPriority",
    "PriorityLevel",
]
