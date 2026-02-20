"""RabbitMQ consumer for Commerce Agent tasks."""
import asyncio
import json
import logging
from typing import Any, Callable

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage

from shared.config import get_settings

logger = logging.getLogger(__name__)


class CRMTaskConsumer:
    """Consumer for Commerce Agent task messages from RabbitMQ.

    Listens on the 'crm_tasks' queue for incoming WhatsApp messages
    that need to be processed by the chatbot.
    """

    def __init__(
        self,
        message_handler: Callable[[dict[str, Any]], asyncio.coroutine],
    ):
        """Initialize the consumer.

        Args:
            message_handler: Async callback function to process messages.
        """
        self._message_handler = message_handler
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._settings = get_settings()

    async def start(self) -> None:
        """Start consuming messages from the queue."""
        queue_name = getattr(self._settings, "rabbitmq_crm_queue", "crm_tasks")

        logger.info(f"Starting CRM task consumer on queue: {queue_name}")

        self._connection = await aio_pika.connect_robust(
            self._settings.rabbitmq_url,
        )

        self._channel = await self._connection.channel()

        # Declare queue with durability
        queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 hours TTL
                "x-dead-letter-exchange": f"{queue_name}.dlx",
            },
        )

        # Declare dead letter exchange
        dlx = await self._channel.declare_exchange(
            f"{queue_name}.dlx",
            ExchangeType.DIRECT,
            durable=True,
        )

        # Declare dead letter queue
        dlq = await self._channel.declare_queue(
            f"{queue_name}.dlq",
            durable=True,
        )

        # Bind DLQ to DLX
        await dlq.bind(dlx, routing_key=queue_name)

        # Set prefetch count
        await self._channel.set_qos(prefetch_count=10)

        # Start consuming
        await queue.consume(self._process_message)

        logger.info(f"CRM task consumer started, listening on queue: {queue_name}")

    async def stop(self) -> None:
        """Stop consuming messages and close connection."""
        logger.info("Stopping CRM task consumer")

        if self._channel:
            await self._channel.close()

        if self._connection:
            await self._connection.close()

        logger.info("CRM task consumer stopped")

    async def _process_message(self, message: AbstractIncomingMessage) -> None:
        """Process an incoming message.

        Args:
            message: The incoming RabbitMQ message.
        """
        async with message.process():
            try:
                # Parse message body
                body = message.body.decode()
                data = json.loads(body)

                logger.debug(f"Processing CRM task: {data.get('message_id', 'unknown')}")

                # Call the message handler
                await self._message_handler(data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
                # Message will be rejected and sent to DLQ
                raise

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                # Re-raise to trigger message rejection
                raise
