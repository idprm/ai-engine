"""Dependency injection for CRM components.

This module provides factory functions for creating CRM repositories,
services, and infrastructure components for use in Gateway controllers.
"""

import logging
from typing import Any

from redis.asyncio import Redis

from shared.config import get_settings

# CRM Infrastructure - Repositories
from commerce_agent.infrastructure.persistence.tenant_repository_impl import TenantRepositoryImpl
from commerce_agent.infrastructure.persistence.customer_repository_impl import CustomerRepositoryImpl
from commerce_agent.infrastructure.persistence.product_repository_impl import ProductRepositoryImpl
from commerce_agent.infrastructure.persistence.order_repository_impl import OrderRepositoryImpl
from commerce_agent.infrastructure.persistence.payment_repository_impl import PaymentRepositoryImpl
from commerce_agent.infrastructure.persistence.label_repository_impl import LabelRepositoryImpl
from commerce_agent.infrastructure.persistence.quick_reply_repository_impl import QuickReplyRepositoryImpl
from commerce_agent.infrastructure.persistence.conversation_repository_impl import ConversationCacheRepository

# CRM Infrastructure - Payment
from commerce_agent.infrastructure.payment.midtrans_client import MidtransClient

# CRM Application Services
from commerce_agent.application.services import (
    CustomerService,
    OrderService,
    ConversationService,
    LabelService,
    QuickReplyService,
)

logger = logging.getLogger(__name__)

# Global Redis client (shared across repositories)
_redis_client: Redis | None = None
_payment_client: MidtransClient | None = None

# Cached repository instances
_tenant_repository: TenantRepositoryImpl | None = None
_customer_repository: CustomerRepositoryImpl | None = None
_product_repository: ProductRepositoryImpl | None = None
_order_repository: OrderRepositoryImpl | None = None
_payment_repository: PaymentRepositoryImpl | None = None
_label_repository: LabelRepositoryImpl | None = None
_conversation_label_repository: Any | None = None  # ConversationLabelRepositoryImpl
_quick_reply_repository: QuickReplyRepositoryImpl | None = None
_conversation_cache_repository: ConversationCacheRepository | None = None


def get_redis_client() -> Redis:
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(settings.redis_url)
    return _redis_client


def get_payment_client() -> MidtransClient:
    """Get or create payment client instance."""
    global _payment_client
    if _payment_client is None:
        settings = get_settings()
        _payment_client = MidtransClient(
            server_key=settings.midtrans_server_key,
            client_key=settings.midtrans_client_key,
            is_production=settings.midtrans_is_production,
        )
    return _payment_client


# Repository Factories

def get_tenant_repository() -> TenantRepositoryImpl:
    """Get tenant repository instance."""
    global _tenant_repository
    if _tenant_repository is None:
        _tenant_repository = TenantRepositoryImpl()
    return _tenant_repository


def get_customer_repository() -> CustomerRepositoryImpl:
    """Get customer repository instance."""
    global _customer_repository
    if _customer_repository is None:
        _customer_repository = CustomerRepositoryImpl()
    return _customer_repository


def get_product_repository() -> ProductRepositoryImpl:
    """Get product repository instance."""
    global _product_repository
    if _product_repository is None:
        _product_repository = ProductRepositoryImpl()
    return _product_repository


def get_order_repository() -> OrderRepositoryImpl:
    """Get order repository instance."""
    global _order_repository
    if _order_repository is None:
        _order_repository = OrderRepositoryImpl()
    return _order_repository


def get_payment_repository() -> PaymentRepositoryImpl:
    """Get payment repository instance."""
    global _payment_repository
    if _payment_repository is None:
        _payment_repository = PaymentRepositoryImpl()
    return _payment_repository


def get_label_repository() -> LabelRepositoryImpl:
    """Get label repository instance."""
    global _label_repository
    if _label_repository is None:
        _label_repository = LabelRepositoryImpl()
    return _label_repository


def get_conversation_label_repository():
    """Get conversation label repository instance."""
    global _conversation_label_repository
    if _conversation_label_repository is None:
        from commerce_agent.infrastructure.persistence.conversation_label_repository_impl import ConversationLabelRepositoryImpl
        _conversation_label_repository = ConversationLabelRepositoryImpl()
    return _conversation_label_repository


def get_quick_reply_repository() -> QuickReplyRepositoryImpl:
    """Get quick reply repository instance."""
    global _quick_reply_repository
    if _quick_reply_repository is None:
        _quick_reply_repository = QuickReplyRepositoryImpl()
    return _quick_reply_repository


def get_conversation_cache_repository() -> ConversationCacheRepository:
    """Get conversation cache repository instance."""
    global _conversation_cache_repository
    if _conversation_cache_repository is None:
        _conversation_cache_repository = ConversationCacheRepository(get_redis_client())
    return _conversation_cache_repository


# Ticket repositories (placeholder - implement when ticket system is added)
def get_ticket_repository():
    """Get ticket repository instance."""
    # TODO: Implement when ticket system is added
    raise NotImplementedError("Ticket repository not yet implemented")


def get_ticket_board_repository():
    """Get ticket board repository instance."""
    # TODO: Implement when ticket system is added
    raise NotImplementedError("Ticket board repository not yet implemented")


def get_ticket_template_repository():
    """Get ticket template repository instance."""
    # TODO: Implement when ticket system is added
    raise NotImplementedError("Ticket template repository not yet implemented")


# Service Factories

def get_customer_service() -> CustomerService:
    """Get customer service instance."""
    return CustomerService(get_customer_repository())


def get_conversation_service() -> ConversationService:
    """Get conversation service instance."""
    return ConversationService(
        conversation_repository=get_conversation_cache_repository(),
        redis_client=get_redis_client(),
    )


def get_order_service() -> OrderService:
    """Get order service instance."""
    return OrderService(
        order_repository=get_order_repository(),
        product_repository=get_product_repository(),
        payment_repository=get_payment_repository(),
        payment_client=get_payment_client(),
    )


def get_label_service() -> LabelService:
    """Get label service instance."""
    return LabelService(
        label_repository=get_label_repository(),
        conversation_label_repository=get_conversation_label_repository(),
    )


def get_quick_reply_service() -> QuickReplyService:
    """Get quick reply service instance."""
    return QuickReplyService(get_quick_reply_repository())


def get_ticket_service():
    """Get ticket service instance."""
    # TODO: Implement when ticket system is added
    raise NotImplementedError("Ticket service not yet implemented")


# Cleanup function for lifespan
async def cleanup_crm_dependencies() -> None:
    """Cleanup CRM dependencies on shutdown."""
    global _redis_client, _payment_client

    logger.info("Cleaning up CRM dependencies...")

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _payment_client:
        await _payment_client.close()
        _payment_client = None

    logger.info("CRM dependencies cleaned up")
