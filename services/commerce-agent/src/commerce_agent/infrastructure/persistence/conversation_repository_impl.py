"""Redis-based implementation of ConversationRepository."""
import json
import logging
from datetime import datetime

from redis.asyncio import Redis

from commerce_agent.domain.entities import Conversation, ConversationMessage
from commerce_agent.domain.repositories import ConversationRepository
from commerce_agent.domain.value_objects import (
    ConversationState,
    CustomerId,
    TenantId,
    OrderId,
    WAChatId,
)
from shared.config import get_settings

logger = logging.getLogger(__name__)


class ConversationCacheRepository(ConversationRepository):
    """Redis-based implementation of ConversationRepository.

    Conversations are cached in Redis with TTL for performance.
    For persistence, they should also be stored in the database.
    """

    def __init__(self, redis: Redis):
        self._redis = redis
        self._ttl = get_settings().redis_job_ttl  # Reuse TTL setting

    def _get_key(self, conversation_id: str) -> str:
        """Get Redis key for a conversation."""
        return f"conversation:{conversation_id}"

    def _get_customer_key(self, customer_id: CustomerId) -> str:
        """Get Redis key for customer's active conversation."""
        return f"customer_conversation:{customer_id.value}"

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        """Retrieve a conversation by its unique identifier."""
        key = self._get_key(conversation_id)
        data = await self._redis.get(key)

        if not data:
            return None

        return self._from_json(data)

    async def get_by_customer(
        self,
        customer_id: CustomerId,
        active_only: bool = True,
    ) -> Conversation | None:
        """Get the conversation for a customer."""
        # Get conversation ID from customer index
        customer_key = self._get_customer_key(customer_id)
        conversation_id = await self._redis.get(customer_key)

        if not conversation_id:
            return None

        conversation_id = conversation_id.decode() if isinstance(conversation_id, bytes) else conversation_id

        if active_only:
            conversation = await self.get_by_id(conversation_id)
            if conversation and conversation.state != ConversationState.COMPLETED:
                return conversation
            return None

        return await self.get_by_id(conversation_id)

    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        state: ConversationState | None = None,
        limit: int = 50,
    ) -> list[Conversation]:
        """List conversations for a tenant.

        Note: This is a simplified implementation. For production,
        consider using a proper database query instead of Redis scan.
        """
        # This would require scanning all conversation keys
        # For now, return empty list as this is primarily a cache
        return []

    async def save(self, conversation: Conversation) -> Conversation:
        """Persist a conversation aggregate."""
        key = self._get_key(conversation.id)
        customer_key = self._get_customer_key(conversation.customer_id)

        data = self._to_json(conversation)

        # Save conversation
        await self._redis.set(key, data, ex=self._ttl)

        # Update customer index
        await self._redis.set(customer_key, conversation.id, ex=self._ttl)

        return conversation

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        key = self._get_key(conversation_id)

        # Get conversation to remove from customer index
        conversation = await self.get_by_id(conversation_id)

        if conversation:
            customer_key = self._get_customer_key(conversation.customer_id)
            await self._redis.delete(customer_key)

        result = await self._redis.delete(key)
        return result > 0

    def _to_json(self, conversation: Conversation) -> str:
        """Serialize conversation to JSON."""
        data = {
            "id": conversation.id,
            "tenant_id": str(conversation.tenant_id),
            "customer_id": str(conversation.customer_id),
            "wa_chat_id": str(conversation.wa_chat_id),
            "messages": [msg.to_dict() for msg in conversation.messages],
            "state": conversation.state.value,
            "context": conversation.context,
            "current_order_id": str(conversation.current_order_id) if conversation.current_order_id else None,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        }
        return json.dumps(data)

    def _from_json(self, data: bytes | str) -> Conversation:
        """Deserialize conversation from JSON."""
        if isinstance(data, bytes):
            data = data.decode()

        obj = json.loads(data)

        conversation = Conversation.__new__(Conversation)
        conversation._id = obj["id"]
        conversation._tenant_id = TenantId.from_string(obj["tenant_id"])
        conversation._customer_id = CustomerId.from_string(obj["customer_id"])
        conversation._wa_chat_id = WAChatId(value=obj["wa_chat_id"])
        conversation._messages = [
            ConversationMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                metadata=msg.get("metadata", {}),
            )
            for msg in obj.get("messages", [])
        ]
        conversation._state = ConversationState(obj["state"])
        conversation._context = obj.get("context", {})
        conversation._current_order_id = (
            OrderId.from_string(obj["current_order_id"])
            if obj.get("current_order_id")
            else None
        )
        conversation._created_at = datetime.fromisoformat(obj["created_at"])
        conversation._updated_at = datetime.fromisoformat(obj["updated_at"])
        conversation._events = []

        return conversation
