"""Commerce Agent service main entry point.

DEPRECATED: This FastAPI application is deprecated. All HTTP routes have been
moved to the Gateway service. Use worker.py for the background worker service.

This file is kept for local development and testing purposes only.
For production, use: python -m commerce_agent.worker
"""
import asyncio
import logging
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from shared.config import get_settings

from commerce_agent.interface.routes import api_router
from commerce_agent.infrastructure.persistence.database import engine, get_db_session
from commerce_agent.infrastructure.persistence.tenant_repository_impl import TenantRepositoryImpl
from commerce_agent.infrastructure.persistence.customer_repository_impl import CustomerRepositoryImpl
from commerce_agent.infrastructure.persistence.product_repository_impl import ProductRepositoryImpl
from commerce_agent.infrastructure.persistence.order_repository_impl import OrderRepositoryImpl
from commerce_agent.infrastructure.persistence.conversation_repository_impl import ConversationCacheRepository
from commerce_agent.infrastructure.persistence.payment_repository_impl import PaymentRepositoryImpl
from commerce_agent.infrastructure.messaging.crm_task_consumer import CRMTaskConsumer
from commerce_agent.infrastructure.messaging.wa_response_publisher import WAResponsePublisher
from commerce_agent.infrastructure.messaging.buffer_flush_worker import BufferFlushWorker
from commerce_agent.infrastructure.cache.message_buffer import MessageBuffer
from commerce_agent.infrastructure.payment.midtrans_client import MidtransClient
from commerce_agent.infrastructure.llm import CRMLangGraphRunner
from commerce_agent.application.services import (
    CustomerService,
    ConversationService,
    OrderService,
    ChatbotOrchestrator,
)
from commerce_agent.application.handlers import WAMessageHandler

# Show deprecation warning
warnings.warn(
    "commerce_agent.main is deprecated. Use commerce_agent.worker for production. "
    "All HTTP routes have been moved to the Gateway service.",
    DeprecationWarning,
    stacklevel=2,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# Global instances
redis_client: Redis | None = None
task_consumer: CRMTaskConsumer | None = None
orchestrator: ChatbotOrchestrator | None = None
message_handler: WAMessageHandler | None = None
buffer_flush_worker: BufferFlushWorker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global redis_client, task_consumer, orchestrator, message_handler, buffer_flush_worker

    logger.info("Starting Commerce Agent service...")

    # Initialize Redis
    redis_client = Redis.from_url(settings.redis_url)

    # Initialize repositories
    tenant_repo = TenantRepositoryImpl()
    customer_repo = CustomerRepositoryImpl()
    product_repo = ProductRepositoryImpl()
    order_repo = OrderRepositoryImpl()
    payment_repo = PaymentRepositoryImpl()
    conversation_repo = ConversationCacheRepository(redis_client)

    # Initialize services
    customer_service = CustomerService(customer_repo)
    conversation_service = ConversationService(conversation_repo, redis_client)

    # Initialize payment client (Midtrans)
    payment_client = MidtransClient(
        server_key=getattr(settings, "midtrans_server_key", ""),
        client_key=getattr(settings, "midtrans_client_key", ""),
        is_production=getattr(settings, "midtrans_is_production", False),
    )

    # Initialize order service
    order_service = OrderService(
        order_repository=order_repo,
        product_repository=product_repo,
        payment_repository=payment_repo,
        payment_client=payment_client,
    )

    # Initialize LLM runner
    llm_runner = CRMLangGraphRunner()

    # Initialize response publisher
    response_publisher = WAResponsePublisher()
    await response_publisher.start()

    # Initialize orchestrator
    # Note: LLM config repository would be from llm_worker
    from llm_worker.infrastructure.persistence.llm_config_repository_impl import LLMConfigRepositoryImpl
    llm_config_repo = LLMConfigRepositoryImpl()

    orchestrator = ChatbotOrchestrator(
        tenant_repository=tenant_repo,
        customer_service=customer_service,
        conversation_service=conversation_service,
        order_service=order_service,
        llm_config_repository=llm_config_repo,
        product_repository=product_repo,
        order_repository=order_repo,
        payment_repository=payment_repo,
        payment_client=payment_client,
        llm_runner=llm_runner,
        response_publisher=response_publisher,
    )
    await orchestrator.start()

    # Initialize message buffer for batching WhatsApp messages
    message_buffer = MessageBuffer(
        redis=redis_client,
        initial_delay=getattr(settings, "message_buffer_initial_delay", 2.0),
        max_delay=getattr(settings, "message_buffer_max_delay", 10.0),
    )
    logger.info("Message buffer initialized")

    # Initialize message handler with buffering
    message_handler = WAMessageHandler(
        orchestrator=orchestrator,
        message_buffer=message_buffer,
    )

    # Initialize buffer flush worker
    async def process_buffered_message(chat_id: str, message: str, metadata: dict):
        """Process a buffered message after flushing."""
        await message_handler.handle_buffered_message(chat_id, message, metadata)

    buffer_flush_worker = BufferFlushWorker(
        message_buffer=message_buffer,
        message_processor=process_buffered_message,
        check_interval=getattr(settings, "buffer_flush_interval", 0.5),
    )

    # Start buffer flush worker as background task
    buffer_flush_task = buffer_flush_worker.start_as_task()
    logger.info("Buffer flush worker started")

    # Initialize and start consumer
    task_consumer = CRMTaskConsumer(
        message_handler=message_handler.handle_message_from_queue,
    )
    consumer_task = asyncio.create_task(task_consumer.start())

    logger.info("Commerce Agent service started")

    yield

    # Cleanup
    logger.info("Stopping Commerce Agent service...")

    if buffer_flush_worker:
        await buffer_flush_worker.stop()

    if task_consumer:
        await task_consumer.stop()

    if orchestrator:
        await orchestrator.stop()

    if redis_client:
        await redis_client.close()

    await payment_client.close()

    logger.info("Commerce Agent service stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Commerce Agent Service",
        description="WhatsApp-based customer chatbot service with multi-tenant CRM",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "commerce_agent",
        }

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": "Commerce Agent",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "commerce_agent.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
