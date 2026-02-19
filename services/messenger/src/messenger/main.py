"""WAHA Sender service main entry point."""
import asyncio
import logging
import signal
import sys

from messenger.application.services import WASenderService
from messenger.infrastructure.cache import RedisCache
from messenger.infrastructure.messaging import WAMessageConsumer
from messenger.infrastructure.waha import WAHAClient
from messenger.interface.handlers import WAMessageHandler
from shared.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
_consumer: WAMessageConsumer | None = None
_cache: RedisCache | None = None
_waha_client: WAHAClient | None = None


async def create_sender_service() -> WASenderService:
    """Create and configure the sender service with dependencies."""
    settings = get_settings()

    # Initialize infrastructure
    cache = RedisCache(url=settings.redis_url)
    await cache.connect()

    waha_client = WAHAClient(
        base_url=settings.waha_server_url,
        api_key=settings.waha_api_key,
        default_session=settings.waha_session,
    )

    # Store globally for cleanup
    global _cache, _waha_client
    _cache = cache
    _waha_client = waha_client

    # Create the sender service
    return WASenderService(
        waha_client=waha_client,
        cache_client=cache,
        cache_ttl=settings.redis_job_ttl,
    )


async def check_waha_connection():
    """Check WAHA server connectivity on startup."""
    settings = get_settings()
    logger.info(f"Connecting to WAHA server at {settings.waha_server_url}...")

    waha_client = WAHAClient(
        base_url=settings.waha_server_url,
        api_key=settings.waha_api_key,
        default_session=settings.waha_session,
    )

    try:
        is_healthy = await waha_client.check_health()
        if is_healthy:
            logger.info("WAHA server is healthy")
        else:
            logger.warning("WAHA server health check failed, will retry on message send")
    except Exception as e:
        logger.warning(f"Could not connect to WAHA server: {e}")
    finally:
        await waha_client.close()


async def run_worker():
    """Main worker loop."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} WAHA Sender in {settings.app_env} mode")

    # Check WAHA connection
    await check_waha_connection()

    # Create sender service
    sender_service = await create_sender_service()

    # Create message handler
    message_handler = WAMessageHandler(sender_service=sender_service)

    # Create and start consumer
    global _consumer
    _consumer = WAMessageConsumer(
        url=settings.rabbitmq_url,
        queue_name=settings.rabbitmq_wa_queue,
    )

    logger.info("WAHA Sender worker started, waiting for messages...")

    try:
        await _consumer.consume(handler=message_handler.handle)
    except asyncio.CancelledError:
        logger.info("Worker cancelled, shutting down...")
    except Exception as e:
        logger.exception(f"Worker error: {e}")
        raise


async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down WAHA Sender...")

    global _consumer, _cache, _waha_client

    if _consumer:
        await _consumer.stop()
        await _consumer.disconnect()

    if _waha_client:
        await _waha_client.close()

    if _cache:
        await _cache.disconnect()

    logger.info("WAHA Sender shutdown complete")


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
