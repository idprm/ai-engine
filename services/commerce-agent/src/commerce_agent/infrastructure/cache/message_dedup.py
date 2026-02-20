"""Message deduplication using Redis."""
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class MessageDeduplication:
    """Redis-based message deduplication.

    Prevents duplicate message processing by tracking message IDs in Redis.
    Uses atomic SET NX EX operation for race-condition-free deduplication.

    Key format: crm:dedup:{tenant_id}:{chat_id}:{message_id}

    Example:
        >>> dedup = MessageDeduplication(redis_client, ttl=300)
        >>> is_dup = await dedup.check_and_mark("tenant1", "chat1", "msg123")
        >>> if is_dup:
        ...     print("Duplicate message, skipping")
    """

    KEY_PREFIX = "crm:dedup:"

    def __init__(self, redis: Redis, ttl: int = 300, enabled: bool = True):
        """Initialize the deduplication service.

        Args:
            redis: Redis client instance.
            ttl: Time-to-live in seconds for dedup keys (default: 300 = 5 minutes).
            enabled: Whether deduplication is enabled.
        """
        self._redis = redis
        self._ttl = ttl
        self._enabled = enabled

    async def check_and_mark(
        self,
        tenant_id: str,
        chat_id: str,
        message_id: str,
    ) -> bool:
        """Check if a message is a duplicate and mark it as seen.

        Uses Redis SET NX EX for atomic check-and-set with TTL.
        This is race-condition safe - if two requests come simultaneously,
        only one will successfully set the key.

        Args:
            tenant_id: The tenant ID.
            chat_id: The WhatsApp chat ID.
            message_id: The unique message ID from WhatsApp.

        Returns:
            True if the message is a duplicate (already processed).
            False if this is a new message (now marked as seen).
        """
        if not self._enabled or not message_id:
            return False

        # Sanitize for Redis key (replace spaces/colons if any)
        safe_tenant = tenant_id.replace(" ", "_").replace(":", "-") if tenant_id else "unknown"
        safe_chat = chat_id.replace(" ", "_").replace(":", "-") if chat_id else "unknown"
        safe_msg = message_id.replace(" ", "_").replace(":", "-")

        key = f"{self.KEY_PREFIX}{safe_tenant}:{safe_chat}:{safe_msg}"

        # SET NX EX - atomic check-and-set with TTL
        # Returns True if the key was set (new message)
        # Returns None/False if key already exists (duplicate)
        was_set = await self._redis.set(key, "1", nx=True, ex=self._ttl)

        if not was_set:
            logger.info(f"Duplicate message detected: {message_id} from {chat_id}")
            return True

        return False

    async def is_duplicate(
        self,
        tenant_id: str,
        chat_id: str,
        message_id: str,
    ) -> bool:
        """Check if a message has been processed without marking it.

        Use this for read-only checks. Use check_and_mark() for the
        typical deduplication flow.

        Args:
            tenant_id: The tenant ID.
            chat_id: The WhatsApp chat ID.
            message_id: The unique message ID from WhatsApp.

        Returns:
            True if the message has been processed, False otherwise.
        """
        if not self._enabled or not message_id:
            return False

        safe_tenant = tenant_id.replace(" ", "_").replace(":", "-") if tenant_id else "unknown"
        safe_chat = chat_id.replace(" ", "_").replace(":", "-") if chat_id else "unknown"
        safe_msg = message_id.replace(" ", "_").replace(":", "-")

        key = f"{self.KEY_PREFIX}{safe_tenant}:{safe_chat}:{safe_msg}"

        return await self._redis.exists(key) > 0
