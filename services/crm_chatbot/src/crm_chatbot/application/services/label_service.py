"""Label application service."""
import logging
from typing import Any

from crm_chatbot.application.dto.label_dto import (
    LabelDTO,
    CreateLabelDTO,
    UpdateLabelDTO,
    ApplyLabelDTO,
    BatchApplyLabelsDTO,
    ConversationLabelsDTO,
    LabelWithConversationsDTO,
)
from crm_chatbot.domain.entities import Label, ConversationLabel
from crm_chatbot.domain.repositories import LabelRepository, ConversationLabelRepository
from crm_chatbot.domain.value_objects import LabelId, TenantId

logger = logging.getLogger(__name__)


class LabelService:
    """Application service for label operations."""

    def __init__(
        self,
        label_repository: LabelRepository,
        conversation_label_repository: ConversationLabelRepository,
    ):
        self._label_repository = label_repository
        self._conversation_label_repository = conversation_label_repository

    async def get_label(self, label_id: str) -> LabelDTO | None:
        """Get a label by ID.

        Args:
            label_id: The label ID.

        Returns:
            LabelDTO if found, None otherwise.
        """
        label = await self._label_repository.get_by_id(
            LabelId.from_string(label_id)
        )

        if not label:
            return None

        return self._to_dto(label)

    async def get_label_by_name(self, tenant_id: str, name: str) -> LabelDTO | None:
        """Get a label by name within a tenant.

        Args:
            tenant_id: The tenant ID.
            name: The label name.

        Returns:
            LabelDTO if found, None otherwise.
        """
        label = await self._label_repository.get_by_name(
            TenantId.from_string(tenant_id),
            name,
        )

        if not label:
            return None

        return self._to_dto(label)

    async def list_labels(
        self,
        tenant_id: str,
        active_only: bool = True,
    ) -> list[LabelDTO]:
        """List all labels for a tenant.

        Args:
            tenant_id: The tenant ID.
            active_only: Whether to only return active labels.

        Returns:
            List of LabelDTOs.
        """
        labels = await self._label_repository.list_by_tenant(
            TenantId.from_string(tenant_id),
            active_only=active_only,
        )

        return [self._to_dto(label) for label in labels]

    async def create_label(
        self,
        tenant_id: str,
        dto: CreateLabelDTO,
    ) -> LabelDTO:
        """Create a new label.

        Args:
            tenant_id: The tenant ID.
            dto: Label creation data.

        Returns:
            Created LabelDTO.

        Raises:
            ValueError: If label name already exists.
        """
        tenant_id_vo = TenantId.from_string(tenant_id)

        # Check if label name already exists
        existing = await self._label_repository.get_by_name(tenant_id_vo, dto.name)
        if existing:
            raise ValueError(f"Label with name '{dto.name}' already exists")

        label = Label.create(
            tenant_id=tenant_id_vo,
            name=dto.name,
            color=dto.color,
            description=dto.description,
        )

        label = await self._label_repository.save(label)
        logger.info(f"Created label: {label.id} for tenant: {tenant_id}")

        return self._to_dto(label)

    async def update_label(
        self,
        label_id: str,
        dto: UpdateLabelDTO,
    ) -> LabelDTO:
        """Update a label.

        Args:
            label_id: The label ID.
            dto: Update data.

        Returns:
            Updated LabelDTO.

        Raises:
            ValueError: If label not found or name conflict.
        """
        label = await self._label_repository.get_by_id(
            LabelId.from_string(label_id)
        )

        if not label:
            raise ValueError(f"Label not found: {label_id}")

        if dto.name is not None:
            # Check for name conflict
            existing = await self._label_repository.get_by_name(
                label.tenant_id,
                dto.name,
            )
            if existing and str(existing.id) != label_id:
                raise ValueError(f"Label with name '{dto.name}' already exists")
            label.update_name(dto.name)

        if dto.color is not None:
            label.update_color(dto.color)

        if dto.description is not None:
            label.update_description(dto.description)

        if dto.is_active is not None:
            if dto.is_active:
                label.activate()
            else:
                label.deactivate()

        label = await self._label_repository.save(label)
        return self._to_dto(label)

    async def delete_label(self, label_id: str) -> bool:
        """Delete a label.

        Args:
            label_id: The label ID.

        Returns:
            True if deleted, False if not found.
        """
        deleted = await self._label_repository.delete(
            LabelId.from_string(label_id)
        )

        if deleted:
            logger.info(f"Deleted label: {label_id}")

        return deleted

    async def apply_label_to_conversation(
        self,
        conversation_id: str,
        dto: ApplyLabelDTO,
        tenant_id: str,
    ) -> LabelDTO:
        """Apply a label to a conversation.

        Args:
            conversation_id: The conversation ID.
            dto: Apply label data.
            tenant_id: The tenant ID.

        Returns:
            The applied LabelDTO.

        Raises:
            ValueError: If label not found.
        """
        label_id = LabelId.from_string(dto.label_id)
        tenant_id_vo = TenantId.from_string(tenant_id)

        # Verify label exists and belongs to tenant
        label = await self._label_repository.get_by_id(label_id)
        if not label:
            raise ValueError(f"Label not found: {dto.label_id}")

        if str(label.tenant_id) != tenant_id:
            raise ValueError("Label does not belong to this tenant")

        # Create association
        conversation_label = ConversationLabel.create(
            conversation_id=conversation_id,
            label_id=label_id,
            tenant_id=tenant_id_vo,
            applied_by=dto.applied_by,
        )

        await self._conversation_label_repository.add_label_to_conversation(
            conversation_label
        )

        logger.info(f"Applied label {dto.label_id} to conversation {conversation_id}")
        return self._to_dto(label)

    async def remove_label_from_conversation(
        self,
        conversation_id: str,
        label_id: str,
    ) -> bool:
        """Remove a label from a conversation.

        Args:
            conversation_id: The conversation ID.
            label_id: The label ID.

        Returns:
            True if removed, False if not found.
        """
        removed = await self._conversation_label_repository.remove_label_from_conversation(
            conversation_id,
            LabelId.from_string(label_id),
        )

        if removed:
            logger.info(f"Removed label {label_id} from conversation {conversation_id}")

        return removed

    async def get_conversation_labels(
        self,
        conversation_id: str,
    ) -> ConversationLabelsDTO:
        """Get all labels for a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            ConversationLabelsDTO with all labels.
        """
        labels = await self._conversation_label_repository.get_labels_for_conversation(
            conversation_id
        )

        return ConversationLabelsDTO(
            conversation_id=conversation_id,
            labels=[self._to_dto(label) for label in labels],
        )

    async def batch_apply_labels(
        self,
        dto: BatchApplyLabelsDTO,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Batch apply labels to multiple conversations.

        Args:
            dto: Batch apply data.
            tenant_id: The tenant ID.

        Returns:
            Result with counts.
        """
        tenant_id_vo = TenantId.from_string(tenant_id)
        label_ids = [LabelId.from_string(lid) for lid in dto.label_ids]

        # Verify all labels exist
        for label_id in label_ids:
            label = await self._label_repository.get_by_id(label_id)
            if not label or str(label.tenant_id) != tenant_id:
                raise ValueError(f"Invalid label: {label_id}")

        # Create all associations
        conversation_labels = []
        for conversation_id in dto.conversation_ids:
            for label_id in label_ids:
                conversation_labels.append(
                    ConversationLabel.create(
                        conversation_id=conversation_id,
                        label_id=label_id,
                        tenant_id=tenant_id_vo,
                        applied_by=dto.applied_by,
                    )
                )

        await self._conversation_label_repository.batch_add_labels(conversation_labels)

        logger.info(
            f"Batch applied {len(label_ids)} labels to "
            f"{len(dto.conversation_ids)} conversations"
        )

        return {
            "conversations_updated": len(dto.conversation_ids),
            "labels_applied": len(label_ids),
            "total_associations": len(conversation_labels),
        }

    async def clear_conversation_labels(
        self,
        conversation_id: str,
    ) -> int:
        """Remove all labels from a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Number of labels removed.
        """
        count = await self._conversation_label_repository.remove_all_labels_from_conversation(
            conversation_id
        )

        logger.info(f"Cleared {count} labels from conversation {conversation_id}")
        return count

    async def get_labels_with_counts(
        self,
        tenant_id: str,
    ) -> list[LabelWithConversationsDTO]:
        """Get all labels with conversation counts.

        Args:
            tenant_id: The tenant ID.

        Returns:
            List of labels with conversation counts.
        """
        labels = await self._label_repository.list_by_tenant(
            TenantId.from_string(tenant_id),
            active_only=False,
        )

        result = []
        for label in labels:
            conversations = await self._conversation_label_repository.get_conversations_for_label(
                label.id,
                limit=10000,  # Get all for count
            )

            result.append(LabelWithConversationsDTO(
                id=str(label.id),
                tenant_id=str(label.tenant_id),
                name=label.name,
                color=label.color,
                description=label.description,
                is_active=label.is_active,
                conversation_count=len(conversations),
                created_at=label.created_at,
                updated_at=label.updated_at,
            ))

        return result

    def _to_dto(self, label: Label) -> LabelDTO:
        """Convert entity to DTO."""
        return LabelDTO(
            id=str(label.id),
            tenant_id=str(label.tenant_id),
            name=label.name,
            color=label.color,
            description=label.description,
            is_active=label.is_active,
            created_at=label.created_at,
            updated_at=label.updated_at,
        )
