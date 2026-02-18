"""RabbitMQ consumer for processing task messages."""
import asyncio
import json
import logging
from typing import Callable, Any

import aio_pika

from shared.config import get_settings

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """RabbitMQ consumer for receiving AI task messages.

    Listens to the task queue and invokes the handler for each message.
    """

    def __init__(
        self,
        url: str | None = None,
        queue_name: str | None = None,
    ):
        settings = get_settings()
        self._url = url or settings.rabbitmq_url
        self._queue_name = queue_name or settings.rabbitmq_task_queue
        self._connection = None
        self._channel = None
        self._queue = None
        self._running = False

    async def connect(self):
        """Establish connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()

        # Set prefetch count for fair dispatch
        await self._channel.set_qos(prefetch_count=1)

        # Declare queue
        self._queue = await self._channel.declare_queue(
            self._queue_name,
            durable=True,
        )

        logger.info(f"Connected to RabbitMQ, consuming from: {self._queue_name}")

    async def disconnect(self):
        """Close RabbitMQ connection."""
        self._running = False
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def consume(self, handler: Callable[[dict[str, Any]], Any]):
        """Start consuming messages from the queue.

        Args:
            handler: Async function to handle each message.
                     Receives the parsed JSON message body.
        """
        await self.connect()
        self._running = True

        logger.info("Starting message consumption...")

        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break

                async with message.process():
                    try:
                        body = json.loads(message.body)
                        logger.debug(f"Received message: {body.get('job_id', 'unknown')}")

                        await handler(body)

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")

                    except Exception as e:
                        logger.exception(f"Error processing message: {e}")
                        # Re-raise to trigger message rejection (nack)
                        raise

    async def stop(self):
        """Stop consuming messages."""
        self._running = False
        logger.info("Stopping message consumption...")
