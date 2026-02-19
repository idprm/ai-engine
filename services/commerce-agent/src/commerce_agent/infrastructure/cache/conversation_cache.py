"""Conversation cache using Redis."""
import json
import logging
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class ConversationCache:
    """Redis-based cache for conversation state.

    Provides fast access to conversation context for the chatbot,
    reducing database queries and improving response time.
    """

    def __init__(self, redis: Redis, ttl: int = 86400):
        """Initialize the cache.

        Args:
            redis: Redis client instance.
            ttl: Time-to-live in seconds (default: 24 hours).
        """
        self._redis = redis
        self._ttl = ttl

    def _get_conversation_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation."""
        return f"crm:conversation:{conversation_id}"

    def _get_customer_conversation_key(self, customer_id: str) -> str:
        """Get Redis key for customer's active conversation mapping."""
        return f"crm:customer:conversation:{customer_id}"

    def _get_context_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation context."""
        return f"crm:context:{conversation_id}"

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Get cached conversation data.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Cached conversation data or None.
        """
        key = self._get_conversation_key(conversation_id)
        data = await self._redis.get(key)

        if data:
            return json.loads(data)
        return None

    async def set_conversation(
        self,
        conversation_id: str,
        data: dict[str, Any],
    ) -> None:
        """Cache conversation data.

        Args:
            conversation_id: The conversation ID.
            data: Conversation data to cache.
        """
        key = self._get_conversation_key(conversation_id)
        await self._redis.set(key, json.dumps(data), ex=self._ttl)

    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete cached conversation.

        Args:
            conversation_id: The conversation ID.
        """
        key = self._get_conversation_key(conversation_id)
        await self._redis.delete(key)

    async def get_customer_conversation_id(self, customer_id: str) -> str | None:
        """Get the active conversation ID for a customer.

        Args:
            customer_id: The customer ID.

        Returns:
            Conversation ID if exists, None otherwise.
        """
        key = self._get_customer_conversation_key(customer_id)
        data = await self._redis.get(key)

        if data:
            return data.decode() if isinstance(data, bytes) else data
        return None

    async def set_customer_conversation_id(
        self,
        customer_id: str,
        conversation_id: str,
    ) -> None:
        """Set the active conversation ID for a customer.

        Args:
            customer_id: The customer ID.
            conversation_id: The conversation ID.
        """
        key = self._get_customer_conversation_key(customer_id)
        await self._redis.set(key, conversation_id, ex=self._ttl)

    async def delete_customer_conversation_id(self, customer_id: str) -> None:
        """Delete the customer's active conversation mapping.

        Args:
            customer_id: The customer ID.
        """
        key = self._get_customer_conversation_key(customer_id)
        await self._redis.delete(key)

    async def get_context(self, conversation_id: str) -> dict[str, Any]:
        """Get conversation context.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Context dictionary (empty if not found).
        """
        key = self._get_context_key(conversation_id)
        data = await self._redis.get(key)

        if data:
            return json.loads(data)
        return {}

    async def set_context(
        self,
        conversation_id: str,
        context: dict[str, Any],
    ) -> None:
        """Set conversation context.

        Args:
            conversation_id: The conversation ID.
            context: Context dictionary.
        """
        key = self._get_context_key(conversation_id)
        await self._redis.set(key, json.dumps(context), ex=self._ttl)

    async def update_context(
        self,
        conversation_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update conversation context with new values.

        Args:
            conversation_id: The conversation ID.
            updates: Key-value pairs to update.

        Returns:
            Updated context dictionary.
        """
        context = await self.get_context(conversation_id)
        context.update(updates)
        await self.set_context(conversation_id, context)
        return context

    async def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a message to the conversation history.

        Args:
            conversation_id: The conversation ID.
            role: Message role (user, assistant, system).
            content: Message content.
            metadata: Optional metadata.
        """
        conversation = await self.get_conversation(conversation_id)

        if not conversation:
            conversation = {
                "id": conversation_id,
                "messages": [],
            }

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        conversation["messages"].append(message)

        # Keep only last 100 messages to prevent unbounded growth
        if len(conversation["messages"]) > 100:
            conversation["messages"] = conversation["messages"][-100:]

        await self.set_conversation(conversation_id, conversation)

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent messages from conversation.

        Args:
            conversation_id: The conversation ID.
            limit: Maximum number of messages to return.

        Returns:
            List of recent messages.
        """
        conversation = await self.get_conversation(conversation_id)

        if not conversation:
            return []

        messages = conversation.get("messages", [])
        return messages[-limit:]

    async def set_state(
        self,
        conversation_id: str,
        state: str,
    ) -> None:
        """Set conversation state.

        Args:
            conversation_id: The conversation ID.
            state: New state value.
        """
        conversation = await self.get_conversation(conversation_id)

        if conversation:
            conversation["state"] = state
            await self.set_conversation(conversation_id, conversation)

    async def get_state(self, conversation_id: str) -> str | None:
        """Get conversation state.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Current state or None.
        """
        conversation = await self.get_conversation(conversation_id)

        if conversation:
            return conversation.get("state")
        return None
