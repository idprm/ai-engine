"""Label repository interface."""
from abc import ABC, abstractmethod

from commerce_agent.domain.entities import Label, ConversationLabel
from commerce_agent.domain.value_objects import LabelId, TenantId


class LabelRepository(ABC):
    """Abstract repository interface for Label entity."""

    @abstractmethod
    async def get_by_id(self, label_id: LabelId) -> Label | None:
        """Retrieve a label by its unique identifier.

        Args:
            label_id: The unique identifier of the label.

        Returns:
            The Label entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_name(self, tenant_id: TenantId, name: str) -> Label | None:
        """Get a label by name within a tenant.

        Args:
            tenant_id: The tenant to search in.
            name: The label name to find.

        Returns:
            The Label if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        active_only: bool = True,
    ) -> list[Label]:
        """List all labels for a tenant.

        Args:
            tenant_id: The tenant to list labels for.
            active_only: Whether to only return active labels.

        Returns:
            List of Label entities.
        """
        pass

    @abstractmethod
    async def save(self, label: Label) -> Label:
        """Persist a label entity.

        Args:
            label: The label to persist.

        Returns:
            The persisted label.
        """
        pass

    @abstractmethod
    async def delete(self, label_id: LabelId) -> bool:
        """Delete a label.

        Args:
            label_id: The unique identifier of the label to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass


class ConversationLabelRepository(ABC):
    """Abstract repository interface for ConversationLabel association."""

    @abstractmethod
    async def get_labels_for_conversation(
        self,
        conversation_id: str,
    ) -> list[Label]:
        """Get all labels applied to a conversation.

        Args:
            conversation_id: The conversation to get labels for.

        Returns:
            List of Label entities applied to the conversation.
        """
        pass

    @abstractmethod
    async def get_conversations_for_label(
        self,
        label_id: LabelId,
        limit: int = 50,
    ) -> list[str]:
        """Get all conversations with a specific label.

        Args:
            label_id: The label to get conversations for.
            limit: Maximum number of conversations to return.

        Returns:
            List of conversation IDs.
        """
        pass

    @abstractmethod
    async def add_label_to_conversation(
        self,
        conversation_label: ConversationLabel,
    ) -> ConversationLabel:
        """Apply a label to a conversation.

        Args:
            conversation_label: The association to create.

        Returns:
            The created association.
        """
        pass

    @abstractmethod
    async def remove_label_from_conversation(
        self,
        conversation_id: str,
        label_id: LabelId,
    ) -> bool:
        """Remove a label from a conversation.

        Args:
            conversation_id: The conversation to remove the label from.
            label_id: The label to remove.

        Returns:
            True if removed, False if not found.
        """
        pass

    @abstractmethod
    async def remove_all_labels_from_conversation(
        self,
        conversation_id: str,
    ) -> int:
        """Remove all labels from a conversation.

        Args:
            conversation_id: The conversation to clear labels from.

        Returns:
            Number of labels removed.
        """
        pass

    @abstractmethod
    async def batch_add_labels(
        self,
        conversation_labels: list[ConversationLabel],
    ) -> list[ConversationLabel]:
        """Apply multiple labels to conversations in batch.

        Args:
            conversation_labels: List of associations to create.

        Returns:
            List of created associations.
        """
        pass
