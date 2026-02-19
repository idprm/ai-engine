"""Data Transfer Objects for CRM chatbot."""

from crm_chatbot.application.dto.message_dto import (
    WhatsAppMessageDTO,
    WhatsAppResponseDTO,
)
from crm_chatbot.application.dto.tenant_dto import (
    CreateTenantDTO,
    TenantDTO,
    UpdateTenantDTO,
)
from crm_chatbot.application.dto.product_dto import (
    CreateProductDTO,
    ProductDTO,
    ProductVariantDTO,
)
from crm_chatbot.application.dto.order_dto import (
    CreateOrderDTO,
    OrderDTO,
    OrderItemDTO,
    UpdateOrderStatusDTO,
)
from crm_chatbot.application.dto.customer_dto import (
    CustomerDTO,
    UpdateCustomerDTO,
)
from crm_chatbot.application.dto.label_dto import (
    LabelDTO,
    CreateLabelDTO,
    UpdateLabelDTO,
    ApplyLabelDTO,
    BatchApplyLabelsDTO,
    ConversationLabelsDTO,
    LabelWithConversationsDTO,
)
from crm_chatbot.application.dto.quick_reply_dto import (
    QuickReplyDTO,
    CreateQuickReplyDTO,
    UpdateQuickReplyDTO,
    QuickReplyListDTO,
)

__all__ = [
    # Message DTOs
    "WhatsAppMessageDTO",
    "WhatsAppResponseDTO",
    # Tenant DTOs
    "CreateTenantDTO",
    "TenantDTO",
    "UpdateTenantDTO",
    # Product DTOs
    "CreateProductDTO",
    "ProductDTO",
    "ProductVariantDTO",
    # Order DTOs
    "CreateOrderDTO",
    "OrderDTO",
    "OrderItemDTO",
    "UpdateOrderStatusDTO",
    # Customer DTOs
    "CustomerDTO",
    "UpdateCustomerDTO",
    # Label DTOs
    "LabelDTO",
    "CreateLabelDTO",
    "UpdateLabelDTO",
    "ApplyLabelDTO",
    "BatchApplyLabelsDTO",
    "ConversationLabelsDTO",
    "LabelWithConversationsDTO",
    # Quick Reply DTOs
    "QuickReplyDTO",
    "CreateQuickReplyDTO",
    "UpdateQuickReplyDTO",
    "QuickReplyListDTO",
]
