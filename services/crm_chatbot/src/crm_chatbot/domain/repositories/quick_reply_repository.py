"""QuickReply repository interface."""
from abc import ABC, abstractmethod

from crm_chatbot.domain.entities import QuickReply
from crm_chatbot.domain.value_objects import QuickReplyId, TenantId


class QuickReplyRepository(ABC):
    """Abstract repository interface for QuickReply entity."""

    @abstractmethod
    async def get_by_id(self, quick_reply_id: QuickReplyId) -> QuickReply | None:
        """Retrieve a quick reply by its unique identifier.

        Args:
            quick_reply_id: The unique identifier of the quick reply.

        Returns:
            The QuickReply entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_shortcut(self, tenant_id: TenantId, shortcut: str) -> QuickReply | None:
        """Get a quick reply by shortcut within a tenant.

        Args:
            tenant_id: The tenant to search in.
            shortcut: The shortcut to find.

        Returns:
            The QuickReply if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[QuickReply]:
        """List all quick replies for a tenant.

        Args:
            tenant_id: The tenant to list quick replies for.
            category: Optional category filter.
            active_only: Whether to only return active quick replies.

        Returns:
            List of QuickReply entities.
        """
        pass

    @abstractmethod
    async def list_categories(self, tenant_id: TenantId) -> list[str]:
        """List all categories used by a tenant.

        Args:
            tenant_id: The tenant to list categories for.

        Returns:
            List of category names.
        """
        pass

    @abstractmethod
    async def save(self, quick_reply: QuickReply) -> QuickReply:
        """Persist a quick reply entity.

        Args:
            quick_reply: The quick reply to persist.

        Returns:
            The persisted quick reply.
        """
        pass

    @abstractmethod
    async def delete(self, quick_reply_id: QuickReplyId) -> bool:
        """Delete a quick reply.

        Args:
            quick_reply_id: The unique identifier of the quick reply to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
