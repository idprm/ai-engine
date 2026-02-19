"""Conversation application service."""
import logging
from typing import Any

from crm_chatbot.domain.entities import Conversation
from crm_chatbot.domain.repositories import ConversationRepository
from crm_chatbot.domain.value_objects import (
    ConversationState,
    CustomerId,
    TenantId,
    OrderId,
    WAChatId,
)
from crm_chatbot.infrastructure.cache import ConversationCache

logger = logging.getLogger(__name__)


class ConversationService:
    """Application service for conversation operations."""

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        conversation_cache: ConversationCache,
    ):
        self._conversation_repository = conversation_repository
        self._conversation_cache = conversation_cache

    async def get_or_create_conversation(
        self,
        tenant_id: str,
        customer_id: str,
        wa_chat_id: str,
    ) -> Conversation:
        """Get existing conversation or create new one.

        Args:
            tenant_id: The tenant ID.
            customer_id: The customer ID.
            wa_chat_id: The WhatsApp chat ID.

        Returns:
            Conversation entity.
        """
        # Try to get from cache first
        cached_id = await self._conversation_cache.get_customer_conversation_id(customer_id)

        if cached_id:
            cached_data = await self._conversation_cache.get_conversation(cached_id)
            if cached_data:
                # Check if conversation is still active
                state = cached_data.get("state", "")
                if state != ConversationState.COMPLETED.value:
                    # Return cached conversation
                    conversation = await self._conversation_repository.get_by_id(cached_id)
                    if conversation:
                        return conversation

        # Try to get from repository
        customer_id_vo = CustomerId.from_string(customer_id)
        conversation = await self._conversation_repository.get_by_customer(
            customer_id_vo,
            active_only=True,
        )

        if conversation:
            # Cache the conversation
            await self._cache_conversation(conversation)
            return conversation

        # Create new conversation
        conversation_id = wa_chat_id  # Use wa_chat_id as conversation_id
        conversation = Conversation.create(
            conversation_id=conversation_id,
            tenant_id=TenantId.from_string(tenant_id),
            customer_id=customer_id_vo,
            wa_chat_id=WAChatId(value=wa_chat_id),
        )

        # Save and cache
        conversation = await self._conversation_repository.save(conversation)
        await self._cache_conversation(conversation)

        logger.info(f"Created conversation: {conversation_id}")
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation.

        Args:
            conversation_id: The conversation ID.
            role: Message role (user, assistant, system).
            content: Message content.
            metadata: Optional metadata.
        """
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return

        conversation.add_message(role, content, metadata)
        await self._conversation_repository.save(conversation)

        # Update cache
        await self._conversation_cache.append_message(
            conversation_id,
            role,
            content,
            metadata,
        )

    async def update_state(
        self,
        conversation_id: str,
        new_state: str,
    ) -> None:
        """Update conversation state.

        Args:
            conversation_id: The conversation ID.
            new_state: New state value.
        """
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return

        conversation.transition_to(ConversationState(new_state))
        await self._conversation_repository.save(conversation)

        # Update cache
        await self._conversation_cache.set_state(conversation_id, new_state)

    async def set_context(
        self,
        conversation_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Set a context value.

        Args:
            conversation_id: The conversation ID.
            key: Context key.
            value: Context value.
        """
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return

        conversation.set_context(key, value)
        await self._conversation_repository.save(conversation)

        # Update cache
        await self._conversation_cache.update_context(conversation_id, {key: value})

    async def get_context(self, conversation_id: str) -> dict[str, Any]:
        """Get conversation context.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Context dictionary.
        """
        # Try cache first
        cached_context = await self._conversation_cache.get_context(conversation_id)
        if cached_context:
            return cached_context

        # Get from repository
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if conversation:
            return conversation.context

        return {}

    async def set_current_order(
        self,
        conversation_id: str,
        order_id: str | None,
    ) -> None:
        """Set the current order for the conversation.

        Args:
            conversation_id: The conversation ID.
            order_id: Order ID or None to clear.
        """
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return

        order_id_vo = OrderId.from_string(order_id) if order_id else None
        conversation.set_current_order(order_id_vo)
        await self._conversation_repository.save(conversation)

        # Update cache
        await self._conversation_cache.update_context(
            conversation_id,
            {"current_order_id": order_id},
        )

    async def get_message_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """Get message history for AI context.

        Args:
            conversation_id: The conversation ID.
            limit: Maximum messages to return.

        Returns:
            List of message dicts with role and content.
        """
        # Try cache first
        cached_messages = await self._conversation_cache.get_messages(conversation_id, limit)

        if cached_messages:
            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in cached_messages
            ]

        # Get from repository
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if conversation:
            return conversation.get_messages_for_llm(limit)

        return []

    async def complete_conversation(self, conversation_id: str) -> None:
        """Mark conversation as completed.

        Args:
            conversation_id: The conversation ID.
        """
        conversation = await self._conversation_repository.get_by_id(conversation_id)

        if conversation:
            conversation.complete()
            await self._conversation_repository.save(conversation)

    async def _cache_conversation(self, conversation: Conversation) -> None:
        """Cache conversation data."""
        await self._conversation_cache.set_customer_conversation_id(
            str(conversation.customer_id),
            conversation.id,
        )

        await self._conversation_cache.set_conversation(
            conversation.id,
            {
                "id": conversation.id,
                "tenant_id": str(conversation.tenant_id),
                "customer_id": str(conversation.customer_id),
                "state": conversation.state.value,
                "context": conversation.context,
            },
        )

        await self._conversation_cache.set_context(
            conversation.id,
            conversation.context,
        )
