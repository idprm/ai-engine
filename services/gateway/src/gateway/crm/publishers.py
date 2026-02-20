"""Publishers for CRM task queue.

This module provides RabbitMQ publishers for sending tasks to the CRM worker
service for processing.
"""

import json
import logging
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, Message

from shared.config import get_settings

logger = logging.getLogger(__name__)

# Global publisher instance
_crm_publisher: "CRMTaskPublisher | None" = None


class CRMTaskPublisher:
    """Publisher for Commerce Agent processing tasks.

    This publisher sends messages to the crm_tasks queue which is consumed
    by the CRM worker service for processing.
    """

    def __init__(self):
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._queue: aio_pika.Queue | None = None

    async def connect(self) -> None:
        """Connect to RabbitMQ and declare queue."""
        settings = get_settings()

        self._connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            client_properties={"connection_name": "gateway-crm-publisher"},
        )

        self._channel = await self._connection.channel()

        # Declare the CRM task queue
        self._queue = await self._channel.declare_queue(
            settings.rabbitmq_crm_queue,
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 hours TTL
                "x-dead-letter-exchange": "crm_tasks.dlx",
            },
        )

        logger.info(f"CRM task publisher connected to queue: {settings.rabbitmq_crm_queue}")

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._queue = None
            logger.info("CRM task publisher disconnected")

    async def publish_webhook_task(self, payload: dict[str, Any]) -> None:
        """Publish a webhook message to the CRM task queue.

        Args:
            payload: The webhook payload to send to CRM worker.
        """
        if not self._channel or not self._queue:
            raise RuntimeError("CRM publisher not connected")

        message = Message(
            body=json.dumps(payload).encode("utf-8"),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )

        await self._channel.default_exchange.publish(
            message,
            routing_key=self._queue.name,
        )

        logger.debug(f"Published webhook task to CRM queue: {payload.get('event', 'unknown')}")

    async def publish_whatsapp_message(
        self,
        session: str,
        chat_id: str,
        message_type: str,
        content: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish a WhatsApp message task to the CRM queue.

        Args:
            session: The WhatsApp session name.
            chat_id: The chat ID (phone number).
            message_type: Type of message (text, image, etc.).
            content: The message content.
            metadata: Optional metadata for processing.
        """
        payload = {
            "type": "whatsapp_message",
            "session": session,
            "chat_id": chat_id,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {},
        }

        await self.publish_webhook_task(payload)

    async def publish_payment_webhook(
        self,
        provider: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish a payment webhook task to the CRM queue.

        Args:
            provider: The payment provider name (midtrans, xendit).
            payload: The webhook payload from the payment provider.
        """
        task_payload = {
            "type": "payment_webhook",
            "provider": provider,
            "payload": payload,
        }

        await self.publish_webhook_task(task_payload)


def get_crm_publisher() -> CRMTaskPublisher:
    """Get the global CRM publisher instance.

    Raises:
        RuntimeError: If publisher not initialized.

    Returns:
        The CRMTaskPublisher instance.
    """
    global _crm_publisher
    if _crm_publisher is None:
        raise RuntimeError("CRM publisher not initialized. Call init_crm_publisher() first.")
    return _crm_publisher


async def init_crm_publisher() -> None:
    """Initialize and connect the global CRM publisher."""
    global _crm_publisher
    _crm_publisher = CRMTaskPublisher()
    await _crm_publisher.connect()
    logger.info("CRM publisher initialized")


async def shutdown_crm_publisher() -> None:
    """Shutdown the global CRM publisher."""
    global _crm_publisher
    if _crm_publisher:
        await _crm_publisher.disconnect()
        _crm_publisher = None
        logger.info("CRM publisher shut down")
