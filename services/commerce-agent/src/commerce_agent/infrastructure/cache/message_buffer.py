"""Message buffer for WhatsApp message batching.

Buffers incoming WhatsApp messages with dynamic delay to handle
customers who send multiple messages in quick succession.

When a customer sends multiple "bubbles" quickly:
  "Halo"           ─┐
  "Saya mau order"  ├─► Buffer (wait 2-3s) ─► Combine ─► Agent processes once
  "Produk A 2 pcs" ─┘

Instead of processing each message individually and generating
multiple responses.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class BufferResult(NamedTuple):
    """Result of adding a message to the buffer.

    Attributes:
        action: Either "BUFFERING" (still waiting) or "FLUSH_READY" (ready to process).
        combined_message: Combined message text (only when FLUSH_READY).
        message_count: Number of messages currently in buffer.
        seconds_until_flush: Seconds until buffer will be flushed.
    """
    action: str  # "BUFFERING" | "FLUSH_READY"
    combined_message: str | None
    message_count: int
    seconds_until_flush: float


@dataclass
class BufferedMessage:
    """A single buffered message.

    Attributes:
        content: The message text.
        timestamp: When the message was received.
    """
    content: str
    timestamp: datetime


class MessageBuffer:
    """Buffers WhatsApp messages with dynamic delay per chat.

    Uses Redis for distributed state, allowing multiple service instances
    to share the same buffer state.

    Buffer Logic:
    1. First message arrives → start timer (2s delay)
    2. Second message arrives within 2s → extend timer (add 2s, max 10s total)
    3. No new messages for delay period → flush buffer and process
    4. Combined message sent to agent as single prompt

    Attributes:
        KEY_PREFIX: Redis key prefix for buffer data.
        INITIAL_DELAY: Initial wait time in seconds after first message.
        EXTEND_DELAY: Seconds to add per new message.
        MAX_DELAY: Maximum total wait time in seconds.
    """

    KEY_PREFIX = "crm:msg_buffer:"
    INITIAL_DELAY = 2.0   # Seconds to wait after first message
    EXTEND_DELAY = 2.0    # Seconds to add per new message
    MAX_DELAY = 10.0      # Maximum total delay

    def __init__(
        self,
        redis: Redis,
        initial_delay: float = 2.0,
        extend_delay: float = 2.0,
        max_delay: float = 10.0,
    ):
        """Initialize the message buffer.

        Args:
            redis: Redis client instance.
            initial_delay: Initial wait time after first message (seconds).
            extend_delay: Time to add per new message (seconds).
            max_delay: Maximum total wait time (seconds).
        """
        self._redis = redis
        self._initial_delay = initial_delay
        self._extend_delay = extend_delay
        self._max_delay = max_delay

    def _get_buffer_key(self, chat_id: str) -> str:
        """Get Redis key for a chat's message buffer.

        Args:
            chat_id: The WhatsApp chat ID.

        Returns:
            Redis key string.
        """
        return f"{self.KEY_PREFIX}{chat_id}"

    async def add_message(
        self,
        chat_id: str,
        message: str,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BufferResult:
        """Add a message to the buffer with dynamic delay.

        Args:
            chat_id: The WhatsApp chat ID.
            message: The message text to buffer.
            timestamp: Optional timestamp (defaults to now).
            metadata: Optional metadata to include with the message.

        Returns:
            BufferResult with buffering status.
        """
        key = self._get_buffer_key(chat_id)
        now = timestamp or datetime.utcnow()

        # Get existing buffer data
        buffer_data = await self._redis.get(key)
        if buffer_data:
            data = json.loads(buffer_data)
            messages = data["messages"]
            first_arrival = datetime.fromisoformat(data["first_arrival"])
            flush_at = datetime.fromisoformat(data["flush_at"])
        else:
            messages = []
            first_arrival = now
            flush_at = now + timedelta(seconds=self._initial_delay)

        # Add new message
        message_entry = {
            "content": message,
            "timestamp": now.isoformat(),
            "metadata": metadata or {},
        }
        messages.append(message_entry)

        # Extend flush time with dynamic delay
        new_flush = now + timedelta(seconds=self._extend_delay)
        time_since_first = (new_flush - first_arrival).total_seconds()

        # Only extend if within max delay
        if time_since_first <= self._max_delay:
            flush_at = new_flush
        else:
            # Cap at max delay from first arrival
            flush_at = first_arrival + timedelta(seconds=self._max_delay)

        # Calculate seconds until flush
        seconds_until_flush = max(0, (flush_at - now).total_seconds())

        # Save buffer with TTL
        data = {
            "chat_id": chat_id,
            "messages": messages,
            "first_arrival": first_arrival.isoformat(),
            "flush_at": flush_at.isoformat(),
            "message_count": len(messages),
        }
        ttl = int(seconds_until_flush) + 5  # Add buffer for processing time
        await self._redis.setex(key, ttl, json.dumps(data))

        logger.debug(
            f"Buffered message {len(messages)} for {chat_id}, "
            f"flush in {seconds_until_flush:.1f}s"
        )

        return BufferResult(
            action="BUFFERING",
            combined_message=None,
            message_count=len(messages),
            seconds_until_flush=seconds_until_flush,
        )

    async def should_flush(self, chat_id: str) -> bool:
        """Check if buffer is ready to flush.

        Args:
            chat_id: The WhatsApp chat ID.

        Returns:
            True if buffer should be flushed, False otherwise.
        """
        key = self._get_buffer_key(chat_id)
        buffer_data = await self._redis.get(key)

        if not buffer_data:
            return False

        data = json.loads(buffer_data)
        flush_at = datetime.fromisoformat(data["flush_at"])

        return datetime.utcnow() >= flush_at

    async def get_combined_message(self, chat_id: str) -> str | None:
        """Get combined message and clear the buffer.

        Args:
            chat_id: The WhatsApp chat ID.

        Returns:
            Combined message text or None if buffer empty.
        """
        key = self._get_buffer_key(chat_id)
        buffer_data = await self._redis.get(key)

        if not buffer_data:
            return None

        data = json.loads(buffer_data)
        messages = data["messages"]

        if not messages:
            return None

        # Combine messages with newline separator
        combined = "\n".join(msg["content"] for msg in messages)

        # Clear the buffer
        await self._redis.delete(key)

        logger.info(
            f"Flushed buffer for {chat_id}: {len(messages)} messages, "
            f"{len(combined)} chars"
        )

        return combined

    async def get_buffer_status(self, chat_id: str) -> dict[str, Any] | None:
        """Get current buffer status for debugging.

        Args:
            chat_id: The WhatsApp chat ID.

        Returns:
            Buffer status dict or None if not found.
        """
        key = self._get_buffer_key(chat_id)
        buffer_data = await self._redis.get(key)

        if not buffer_data:
            return None

        data = json.loads(buffer_data)
        flush_at = datetime.fromisoformat(data["flush_at"])

        return {
            "chat_id": chat_id,
            "message_count": len(data["messages"]),
            "first_arrival": data["first_arrival"],
            "flush_at": data["flush_at"],
            "seconds_until_flush": max(0,
                (flush_at - datetime.utcnow()).total_seconds()
            ),
            "messages": [
                {"content": msg["content"][:50], "timestamp": msg["timestamp"]}
                for msg in data["messages"]
            ],
        }

    async def get_all_active_chat_ids(self) -> list[str]:
        """Get all chat IDs with active buffers.

        Scans Redis for buffer keys and extracts chat IDs.

        Returns:
            List of chat IDs with active buffers.
        """
        chat_ids = []
        pattern = f"{self.KEY_PREFIX}*"

        # Use SCAN to avoid blocking
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor,
                match=pattern,
                count=100,
            )

            for key in keys:
                # Extract chat_id from key
                key_str = key.decode() if isinstance(key, bytes) else key
                chat_id = key_str.replace(self.KEY_PREFIX, "")
                chat_ids.append(chat_id)

            if cursor == 0:
                break

        return chat_ids

    async def force_flush(self, chat_id: str) -> str | None:
        """Force flush a buffer regardless of timing.

        Args:
            chat_id: The WhatsApp chat ID.

        Returns:
            Combined message or None if buffer empty.
        """
        logger.info(f"Force flushing buffer for {chat_id}")
        return await self.get_combined_message(chat_id)

    async def clear_buffer(self, chat_id: str) -> bool:
        """Clear a buffer without processing.

        Args:
            chat_id: The WhatsApp chat ID.

        Returns:
            True if buffer was cleared, False if not found.
        """
        key = self._get_buffer_key(chat_id)
        deleted = await self._redis.delete(key)

        if deleted:
            logger.info(f"Cleared buffer for {chat_id}")

        return deleted > 0
