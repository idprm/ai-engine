"""AI Engine service main entry point."""
import asyncio
import logging
import signal
import sys

from llm_worker.application.services import ProcessingService
from llm_worker.infrastructure.cache import RedisCache
from llm_worker.infrastructure.llm import LangGraphRunner
from llm_worker.infrastructure.messaging import RabbitMQConsumer
from llm_worker.infrastructure.persistence import (
    LLMConfigRepositoryImpl,
    PromptTemplateRepositoryImpl,
)
from llm_worker.interface.handlers import MessageHandler
from shared.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
_consumer: RabbitMQConsumer | None = None
_cache: RedisCache | None = None


async def create_processing_service() -> ProcessingService:
    """Create and configure the processing service with dependencies."""
    settings = get_settings()

    # Initialize infrastructure
    cache = RedisCache(url=settings.redis_url)
    await cache.connect()

    # Store globally for cleanup
    global _cache
    _cache = cache

    # Create the processing service
    return ProcessingService(
        llm_config_repository=LLMConfigRepositoryImpl(),
        prompt_template_repository=PromptTemplateRepositoryImpl(),
        llm_runner=LangGraphRunner(),
        cache_client=cache,
        cache_ttl=settings.redis_job_ttl,
    )


async def run_worker():
    """Main worker loop."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} AI Engine in {settings.app_env} mode")

    # Create processing service
    processing_service = await create_processing_service()

    # Create message handler
    message_handler = MessageHandler(processing_service=processing_service)

    # Create and start consumer
    global _consumer
    _consumer = RabbitMQConsumer(
        url=settings.rabbitmq_url,
        queue_name=settings.rabbitmq_task_queue,
    )

    logger.info("AI Engine worker started, waiting for tasks...")

    try:
        await _consumer.consume(handler=message_handler.handle)
    except asyncio.CancelledError:
        logger.info("Worker cancelled, shutting down...")
    except Exception as e:
        logger.exception(f"Worker error: {e}")
        raise


async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down AI Engine...")

    global _consumer, _cache

    if _consumer:
        await _consumer.stop()
        await _consumer.disconnect()

    if _cache:
        await _cache.disconnect()

    logger.info("AI Engine shutdown complete")


def signal_handler(loop):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal")

    # Stop the consumer
    global _consumer
    if _consumer:
        asyncio.create_task(_consumer.stop())

    # Cancel all tasks
    for task in asyncio.all_tasks(loop):
        task.cancel()


async def main():
    """Main entry point."""
    loop = asyncio.get_event_loop()

    # Setup signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: signal_handler(loop),
        )

    try:
        await run_worker()
    except asyncio.CancelledError:
        pass
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        sys.exit(0)
