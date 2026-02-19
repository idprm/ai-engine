"""API routes configuration."""
from fastapi import APIRouter

from crm_chatbot.interface.controllers import (
    tenant_controller,
    product_controller,
    order_controller,
    webhook_controller,
    label_router,
    conversation_label_router,
    batch_label_router,
    quick_reply_router,
)


def create_api_router() -> APIRouter:
    """Create and configure the main API router."""
    router = APIRouter(prefix="/v1/crm")

    # Include tenant routes
    router.include_router(tenant_controller.router)

    # Include product routes (nested under tenants)
    router.include_router(product_controller.router)

    # Include order routes
    router.include_router(order_controller.router)

    # Include webhook routes
    router.include_router(webhook_controller.router)

    # Include label routes
    router.include_router(label_router)

    # Include conversation label routes
    router.include_router(conversation_label_router)

    # Include batch label routes
    router.include_router(batch_label_router)

    # Include quick reply routes
    router.include_router(quick_reply_router)

    return router


# Create the router instance
api_router = create_api_router()
