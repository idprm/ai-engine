"""Controllers for CRM chatbot API."""

from crm_chatbot.interface.controllers.tenant_controller import TenantController
from crm_chatbot.interface.controllers.product_controller import ProductController
from crm_chatbot.interface.controllers.order_controller import OrderController
from crm_chatbot.interface.controllers.webhook_controller import WebhookController
from crm_chatbot.interface.controllers.label_controller import (
    router as label_router,
    conversation_router as conversation_label_router,
    batch_router as batch_label_router,
)
from crm_chatbot.interface.controllers.quick_reply_controller import (
    router as quick_reply_router,
)

__all__ = [
    "TenantController",
    "ProductController",
    "OrderController",
    "WebhookController",
    "label_router",
    "conversation_label_router",
    "batch_label_router",
    "quick_reply_router",
]
