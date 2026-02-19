"""RabbitMQ publisher for WhatsApp response messages."""
import json
import logging
import uuid
from typing import Any

import aio_pika

from shared.config import get_settings

logger = logging.getLogger(__name__)


class WAResponsePublisher:
    """Publisher for WhatsApp response messages.

    Publishes messages to the 'wa_messages' queue for the WAHA Sender
    service to send via WhatsApp.
    """

    def __init__(self):
        """Initialize the publisher."""
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.RobustExchange | None = None
        self._settings = get_settings()

    async def start(self) -> None:
        """Initialize the connection and channel."""
        logger.info("Starting WA response publisher")

        self._connection = await aio_pika.connect_robust(
            self._settings.rabbitmq_url,
        )

        self._channel = await self._connection.channel()

        # Declare exchange
        self._exchange = await self._channel.declare_exchange(
            self._settings.rabbitmq_event_exchange,
            ExchangeType.DIRECT,
            durable=True,
        )

        # Ensure queue exists
        await self._channel.declare_queue(
            self._settings.rabbitmq_wa_queue,
            durable=True,
        )

        logger.info("WA response publisher started")

    async def stop(self) -> None:
        """Close the connection."""
        logger.info("Stopping WA response publisher")

        if self._channel:
            await self._channel.close()

        if self._connection:
            await self._connection.close()

        logger.info("WA response publisher stopped")

    async def publish_message(
        self,
        wa_session: str,
        chat_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Publish a WhatsApp message to be sent.

        Args:
            wa_session: The WAHA session name to use.
            chat_id: The WhatsApp chat ID to send to.
            text: The message text to send.
            metadata: Optional metadata for logging/tracking.

        Returns:
            The message ID.
        """
        if not self._exchange:
            raise RuntimeError("Publisher not started. Call start() first.")

        message_id = str(uuid.uuid4())

        payload = {
            "message_id": message_id,
            "wa_session": wa_session,
            "chat_id": chat_id,
            "text": text,
            "metadata": metadata or {},
        }

        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            message_id=message_id,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self._exchange.publish(
            message,
            routing_key=self._settings.rabbitmq_wa_queue,
        )

        logger.debug(f"Published WA message: {message_id} to {chat_id}")

        return message_id

    async def publish_typing_indicator(
        self,
        wa_session: str,
        chat_id: str,
        is_typing: bool = True,
    ) -> None:
        """Publish a typing indicator message.

        Args:
            wa_session: The WAHA session name to use.
            chat_id: The WhatsApp chat ID.
            is_typing: Whether to show typing indicator.
        """
        if not self._exchange:
            raise RuntimeError("Publisher not started. Call start() first.")

        payload = {
            "message_id": str(uuid.uuid4()),
            "wa_session": wa_session,
            "chat_id": chat_id,
            "action": "typing" if is_typing else "stop_typing",
            "metadata": {},
        }

        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.NOT_PERSISTENT,
        )

        await self._exchange.publish(
            message,
            routing_key=self._settings.rabbitmq_wa_queue,
        )
