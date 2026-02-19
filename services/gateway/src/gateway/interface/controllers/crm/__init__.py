"""CRM controllers for Gateway service.

These controllers were migrated from the CRM chatbot service to consolidate
all HTTP API handling in the Gateway service.
"""

from gateway.interface.controllers.crm.tenant_controller import router as tenant_router
from gateway.interface.controllers.crm.product_controller import router as product_router
from gateway.interface.controllers.crm.order_controller import router as order_router
from gateway.interface.controllers.crm.webhook_controller import router as webhook_router
from gateway.interface.controllers.crm.label_controller import (
    router as label_router,
    conversation_router as conversation_label_router,
    batch_router as batch_label_router,
)
from gateway.interface.controllers.crm.quick_reply_controller import router as quick_reply_router

__all__ = [
    "tenant_router",
    "product_router",
    "order_router",
    "webhook_router",
    "label_router",
    "conversation_label_router",
    "batch_label_router",
    "quick_reply_router",
]
