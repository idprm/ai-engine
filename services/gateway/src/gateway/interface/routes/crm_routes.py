"""CRM routes for Gateway service.

This module defines the API routes for CRM functionality that was migrated
from the CRM chatbot service.
"""

from fastapi import APIRouter

from gateway.interface.controllers.crm import (
    tenant_router,
    product_router,
    order_router,
    webhook_router,
    label_router,
    conversation_label_router,
    batch_label_router,
    quick_reply_router,
)

# Main CRM router with all sub-routers
crm_router = APIRouter(prefix="/v1/crm")

# Include all CRM controllers
crm_router.include_router(tenant_router)
crm_router.include_router(product_router)
crm_router.include_router(order_router)
crm_router.include_router(webhook_router)
crm_router.include_router(label_router)
crm_router.include_router(conversation_label_router)
crm_router.include_router(batch_label_router)
crm_router.include_router(quick_reply_router)
