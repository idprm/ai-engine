"""CRM context module for Gateway service.

This module provides dependency injection and publishers for CRM components
that are shared between Gateway and CRM Worker services.
"""

from gateway.crm.dependencies import (
    get_tenant_repository,
    get_customer_repository,
    get_product_repository,
    get_order_repository,
    get_payment_repository,
    get_label_repository,
    get_conversation_label_repository,
    get_quick_reply_repository,
    get_conversation_cache_repository,
    get_customer_service,
    get_order_service,
    get_conversation_service,
    get_label_service,
    get_quick_reply_service,
    get_payment_client,
    get_redis_client,
    cleanup_crm_dependencies,
)
from gateway.crm.publishers import (
    CRMTaskPublisher,
    get_crm_publisher,
    init_crm_publisher,
    shutdown_crm_publisher,
)

__all__ = [
    # Repositories
    "get_tenant_repository",
    "get_customer_repository",
    "get_product_repository",
    "get_order_repository",
    "get_payment_repository",
    "get_label_repository",
    "get_conversation_label_repository",
    "get_quick_reply_repository",
    "get_conversation_cache_repository",
    # Services
    "get_customer_service",
    "get_order_service",
    "get_conversation_service",
    "get_label_service",
    "get_quick_reply_service",
    # Infrastructure
    "get_payment_client",
    "get_redis_client",
    "cleanup_crm_dependencies",
    # Publishers
    "get_crm_publisher",
    "init_crm_publisher",
    "shutdown_crm_publisher",
    "CRMTaskPublisher",
]
