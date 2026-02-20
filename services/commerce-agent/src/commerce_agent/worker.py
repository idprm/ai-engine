"""Commerce Agent Worker - Background message processor.

This is the main entry point for the Commerce Agent worker service.
It consumes messages from the CRM task queue and processes them using
the AI agent and messaging infrastructure.

The worker is designed to run without HTTP endpoints - all API routes
have been moved to the Gateway service.
"""
import asyncio
import logging
import signal

from redis.asyncio import Redis

from shared.config import get_settings

from commerce_agent.infrastructure.persistence import (
    TenantRepositoryImpl,
    CustomerRepositoryImpl,
    ProductRepositoryImpl,
    OrderRepositoryImpl,
    PaymentRepositoryImpl,
    ConversationCacheRepository,
)
from commerce_agent.infrastructure.messaging.crm_task_consumer import CRMTaskConsumer
from commerce_agent.infrastructure.messaging.wa_response_publisher import WAResponsePublisher
from commerce_agent.infrastructure.messaging.buffer_flush_worker import BufferFlushWorker
from commerce_agent.infrastructure.cache.message_buffer import MessageBuffer
from commerce_agent.infrastructure.cache.message_dedup import MessageDeduplication
from commerce_agent.infrastructure.payment.midtrans_client import MidtransClient
from commerce_agent.infrastructure.llm import CRMLangGraphRunner
from commerce_agent.application.services import (
    CustomerService,
    ConversationService,
    OrderService,
    ChatbotOrchestrator,
)
from commerce_agent.application.handlers import WAMessageHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main worker entry point."""
    settings = get_settings()
    logger.info("Starting Commerce Agent Worker...")

    # Global instances
    redis_client: Redis | None = None
    task_consumer: CRMTaskConsumer | None = None
    orchestrator: ChatbotOrchestrator | None = None
    message_handler: WAMessageHandler | None = None
    buffer_flush_worker: BufferFlushWorker | None = None
    buffer_flush_task = None
    consumer_task = None

    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Initialize Redis
        redis_client = Redis.from_url(settings.redis_url)
        logger.info("Redis client initialized")

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
        logger.info("WA response publisher started")

        # Initialize LLM config repository from llm_worker
        from llm_worker.infrastructure.persistence.llm_config_repository_impl import LLMConfigRepositoryImpl
        llm_config_repo = LLMConfigRepositoryImpl()

        # Initialize orchestrator
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
        logger.info("Chatbot orchestrator started")

        # Initialize message buffer for batching WhatsApp messages
        message_buffer = MessageBuffer(
            redis=redis_client,
            initial_delay=getattr(settings, "message_buffer_initial_delay", 2.0),
            max_delay=getattr(settings, "message_buffer_max_delay", 10.0),
        )
        logger.info("Message buffer initialized")

        # Initialize message deduplication
        message_dedup = MessageDeduplication(
            redis=redis_client,
            ttl=getattr(settings, "message_dedup_ttl", 300),
            enabled=getattr(settings, "message_dedup_enabled", True),
        )
        logger.info("Message deduplication initialized")

        # Initialize message handler with buffering
        message_handler = WAMessageHandler(
            orchestrator=orchestrator,
            message_buffer=message_buffer,
            message_dedup=message_dedup,
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

        logger.info("Commerce Agent Worker started successfully")
        logger.info("Waiting for messages...")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        logger.info("Shutting down Commerce Agent Worker...")

        if buffer_flush_worker:
            await buffer_flush_worker.stop()
            logger.info("Buffer flush worker stopped")

        if task_consumer:
            await task_consumer.stop()
            logger.info("Task consumer stopped")

        if consumer_task:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

        if buffer_flush_task:
            buffer_flush_task.cancel()
            try:
                await buffer_flush_task
            except asyncio.CancelledError:
                pass

        if orchestrator:
            await orchestrator.stop()
            logger.info("Orchestrator stopped")

        if redis_client:
            await redis_client.close()
            logger.info("Redis client closed")

        logger.info("Commerce Agent Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
