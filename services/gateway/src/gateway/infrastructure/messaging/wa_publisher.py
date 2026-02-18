"""RabbitMQ publisher for WhatsApp messages."""
import json
import logging
from typing import Any

import aio_pika

from shared.config import get_settings

logger = logging.getLogger(__name__)


class WAMessagePublisher:
    """RabbitMQ publisher for WhatsApp messages.

    Publishes messages to the WA queue for waha-sender to consume.
    """

    def __init__(self, url: str | None = None, queue_name: str | None = None):
        settings = get_settings()
        self._url = url or settings.rabbitmq_url
        self._queue_name = queue_name or settings.rabbitmq_wa_queue
        self._connection = None
        self._channel = None

    async def connect(self):
        """Establish connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.declare_queue(self._queue_name, durable=True)
        logger.info(f"Connected to RabbitMQ, WA queue: {self._queue_name}")

    async def disconnect(self):
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ WA publisher")

    async def publish_wa_message(self, message: dict[str, Any]) -> None:
        """Publish a WhatsApp message to the queue.

        Args:
            message: The message payload containing chat_id, text, session, etc.
        """
        await self.connect()

        message_body = aio_pika.Message(
            body=json.dumps(message).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=message.get("job_id", ""),
        )

        await self._channel.default_exchange.publish(
            message_body,
            routing_key=self._queue_name,
        )

        logger.debug(f"Published WA message to {message.get('chat_id', 'unknown')}")
