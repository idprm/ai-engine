"""RabbitMQ message publisher implementation."""
import json
import logging
from typing import Any

import aio_pika

from shared.config import get_settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """RabbitMQ publisher for task messages.

    Publishes messages to the task queue for LLM Worker to consume.
    """

    def __init__(self, url: str | None = None, queue_name: str | None = None):
        settings = get_settings()
        self._url = url or settings.rabbitmq_url
        self._queue_name = queue_name or settings.rabbitmq_task_queue
        self._connection = None
        self._channel = None

    async def connect(self):
        """Establish connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.declare_queue(self._queue_name, durable=True)
        logger.info(f"Connected to RabbitMQ, queue: {self._queue_name}")

    async def disconnect(self):
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def publish_task(self, job_id: str, message: dict[str, Any]) -> None:
        """Publish a task message to the queue.

        Args:
            job_id: The job identifier.
            message: The message payload.
        """
        await self.connect()

        message_body = aio_pika.Message(
            body=json.dumps(message).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=job_id,
        )

        await self._channel.default_exchange.publish(
            message_body,
            routing_key=self._queue_name,
        )

        logger.debug(f"Published task for job {job_id}")
