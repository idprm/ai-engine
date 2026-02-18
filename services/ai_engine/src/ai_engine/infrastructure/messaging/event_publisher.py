"""Event publisher for publishing processing events."""
import json
import logging
from typing import Any

import aio_pika

from shared.config import get_settings

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publisher for domain events to RabbitMQ.

    Publishes events to the event exchange for other services to consume.
    """

    def __init__(
        self,
        url: str | None = None,
        exchange_name: str | None = None,
    ):
        settings = get_settings()
        self._url = url or settings.rabbitmq_url
        self._exchange_name = exchange_name or settings.rabbitmq_event_exchange
        self._connection = None
        self._channel = None
        self._exchange = None

    async def connect(self):
        """Establish connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()

        # Declare exchange
        self._exchange = await self._channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        logger.info(f"Connected to event exchange: {self._exchange_name}")

    async def disconnect(self):
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from event exchange")

    async def publish(self, event_type: str, data: dict[str, Any], routing_key: str | None = None):
        """Publish an event to the exchange.

        Args:
            event_type: Type of event (e.g., "processing.completed").
            data: Event payload.
            routing_key: Optional routing key (defaults to event_type).
        """
        await self.connect()

        message_body = {
            "event_type": event_type,
            "data": data,
        }

        message = aio_pika.Message(
            body=json.dumps(message_body).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        routing_key = routing_key or event_type

        await self._exchange.publish(
            message,
            routing_key=routing_key,
        )

        logger.debug(f"Published event: {event_type}")
