"""Data Transfer Objects for CRM chatbot."""

from commerce_agent.application.dto.message_dto import (
    WhatsAppMessageDTO,
    WhatsAppResponseDTO,
)
from commerce_agent.application.dto.tenant_dto import (
    CreateTenantDTO,
    TenantDTO,
    UpdateTenantDTO,
)
from commerce_agent.application.dto.product_dto import (
    CreateProductDTO,
    ProductDTO,
    ProductVariantDTO,
)
from commerce_agent.application.dto.order_dto import (
    CreateOrderDTO,
    OrderDTO,
    OrderItemDTO,
    UpdateOrderStatusDTO,
)
from commerce_agent.application.dto.customer_dto import (
    CustomerDTO,
    UpdateCustomerDTO,
)
from commerce_agent.application.dto.label_dto import (
    LabelDTO,
    CreateLabelDTO,
    UpdateLabelDTO,
    ApplyLabelDTO,
    BatchApplyLabelsDTO,
    ConversationLabelsDTO,
    LabelWithConversationsDTO,
)
from commerce_agent.application.dto.quick_reply_dto import (
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
