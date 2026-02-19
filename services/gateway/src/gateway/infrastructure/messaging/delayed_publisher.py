"""Delayed message publisher for retry scheduling.

This module provides a publisher for scheduling delayed task retries
using RabbitMQ's dead-letter queue pattern with TTL.
"""
import json
import logging
from datetime import datetime
from typing import Any

import aio_pika
from aio_pika import DeliveryMode

from shared.config import get_settings

logger = logging.getLogger(__name__)


class DelayedTaskPublisher:
    """Publisher for delayed task messages using dead-letter queue pattern.

    Uses RabbitMQ's message TTL and dead-letter exchange features to
    schedule messages for delayed delivery.

    How it works:
    1. Create a delay queue with TTL (message time-to-live)
    2. Configure the delay queue to dead-letter to the main task queue
    3. Publish message to delay queue
    4. After TTL expires, RabbitMQ routes message to main queue
    """

    def __init__(
        self,
        url: str | None = None,
        task_queue: str | None = None,
    ):
        settings = get_settings()
        self._url = url or settings.rabbitmq_url
        self._task_queue = task_queue or settings.rabbitmq_task_queue
        self._connection = None
        self._channel = None
        self._declared_delays: set[int] = set()  # Track declared delay queues

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()

        # Declare main task queue
        await self._channel.declare_queue(self._task_queue, durable=True)

        logger.info(f"Connected to RabbitMQ for delayed publishing, task queue: {self._task_queue}")

    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ delayed publisher")

    async def schedule_retry(
        self,
        job_id: str,
        message: dict[str, Any],
        delay_seconds: float,
    ) -> None:
        """Schedule a job retry after a delay.

        Uses RabbitMQ's dead-letter queue pattern with TTL to delay
        the message before it's delivered to the main task queue.

        Args:
            job_id: The job identifier.
            message: The message payload (will be updated with retry info).
            delay_seconds: Delay in seconds before the message should be processed.
        """
        await self.connect()

        # Round delay to nearest 100ms for queue reuse
        delay_ms = max(100, int(delay_seconds * 1000))

        # Get or create delay queue
        delay_queue_name = f"{self._task_queue}.delay.{delay_ms}ms"

        # Only declare the queue once per delay duration
        if delay_ms not in self._declared_delays:
            await self._channel.declare_queue(
                delay_queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": delay_ms,
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": self._task_queue,
                },
            )
            self._declared_delays.add(delay_ms)
            logger.debug(f"Declared delay queue: {delay_queue_name} with TTL={delay_ms}ms")

        # Update message with retry scheduling info
        message["retry_scheduled_at"] = datetime.utcnow().isoformat()
        message["retry_delay_seconds"] = delay_seconds

        # Create message
        message_body = aio_pika.Message(
            body=json.dumps(message).encode(),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=job_id,
            headers={
                "x-retry-delay-ms": delay_ms,
                "x-retry-scheduled-at": datetime.utcnow().isoformat(),
            },
        )

        # Publish to delay queue
        await self._channel.default_exchange.publish(
            message_body,
            routing_key=delay_queue_name,
        )

        logger.info(
            f"Scheduled retry for job {job_id} in {delay_seconds:.2f}s "
            f"(queue: {delay_queue_name})"
        )

    async def schedule_retry_with_backoff(
        self,
        job_id: str,
        message: dict[str, Any],
        attempt: int,
        base_delay: float = 5.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
    ) -> None:
        """Schedule a retry with exponential backoff.

        Calculates the delay based on attempt number using exponential backoff,
        then schedules the retry.

        Args:
            job_id: The job identifier.
            message: The message payload.
            attempt: Current attempt number (0-indexed).
            base_delay: Base delay in seconds.
            max_delay: Maximum delay cap in seconds.
            multiplier: Backoff multiplier.
        """
        # Calculate exponential delay
        delay = min(base_delay * (multiplier**attempt), max_delay)

        await self.schedule_retry(job_id, message, delay)

    async def cancel_pending_retries(self, job_id: str) -> int:
        """Cancel pending retries for a job.

        Note: This is a best-effort operation. Messages already in delay queues
        cannot be selectively removed without additional infrastructure.

        Args:
            job_id: The job identifier.

        Returns:
            Number of messages cancelled (always 0 for this implementation).
        """
        # With the dead-letter queue pattern, we cannot selectively
        # remove messages from delay queues without a more complex setup.
        # This would require:
        # 1. Using a separate exchange per job
        # 2. Or using RabbitMQ's delayed message exchange plugin
        # 3. Or tracking retry IDs and ignoring them on consumption

        logger.warning(
            f"Cannot cancel pending retries for job {job_id} with current implementation. "
            "Consider implementing consumer-side deduplication."
        )
        return 0

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about delay queues.

        Returns:
            Dictionary with delay queue information.
        """
        await self.connect()

        stats = {
            "declared_delays": list(self._declared_delays),
            "task_queue": self._task_queue,
            "delay_queues_count": len(self._declared_delays),
        }

        return stats
