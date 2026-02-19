"""Conversation repository interface."""
from abc import ABC, abstractmethod

from commerce_agent.domain.entities import Conversation
from commerce_agent.domain.value_objects import ConversationState, CustomerId, TenantId


class ConversationRepository(ABC):
    """Abstract repository interface for Conversation aggregate."""

    @abstractmethod
    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        """Retrieve a conversation by its unique identifier.

        Args:
            conversation_id: The unique identifier of the conversation.

        Returns:
            The Conversation aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_customer(
        self,
        customer_id: CustomerId,
        active_only: bool = True,
    ) -> Conversation | None:
        """Get the conversation for a customer.

        Args:
            customer_id: The customer to get the conversation for.
            active_only: Whether to only return active conversations.

        Returns:
            The Conversation if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        state: ConversationState | None = None,
        limit: int = 50,
    ) -> list[Conversation]:
        """List conversations for a tenant.

        Args:
            tenant_id: The tenant to list conversations for.
            state: Optional state filter.
            limit: Maximum number of conversations to return.

        Returns:
            List of Conversation aggregates.
        """
        pass

    @abstractmethod
    async def save(self, conversation: Conversation) -> Conversation:
        """Persist a conversation aggregate.

        Args:
            conversation: The conversation to persist.

        Returns:
            The persisted conversation.
        """
        pass

    @abstractmethod
    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The unique identifier of the conversation to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
