"""SQLAlchemy implementation of LabelRepository."""
import logging
from uuid import UUID

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from commerce_agent.domain.entities import Label, ConversationLabel
from commerce_agent.domain.repositories import LabelRepository, ConversationLabelRepository
from commerce_agent.domain.value_objects import LabelId, TenantId
from commerce_agent.infrastructure.persistence.database import get_db_session
from commerce_agent.infrastructure.persistence.models import LabelModel, ConversationLabelModel

logger = logging.getLogger(__name__)


class LabelRepositoryImpl(LabelRepository):
    """SQLAlchemy implementation of LabelRepository."""

    async def get_by_id(self, label_id: LabelId) -> Label | None:
        """Retrieve a label by its unique identifier."""
        async with get_db_session() as session:
            result = await session.execute(
                select(LabelModel).where(LabelModel.id == label_id.value)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_name(self, tenant_id: TenantId, name: str) -> Label | None:
        """Get a label by name within a tenant."""
        async with get_db_session() as session:
            result = await session.execute(
                select(LabelModel).where(
                    and_(
                        LabelModel.tenant_id == tenant_id.value,
                        LabelModel.name == name,
                    )
                )
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        active_only: bool = True,
    ) -> list[Label]:
        """List all labels for a tenant."""
        async with get_db_session() as session:
            query = select(LabelModel).where(LabelModel.tenant_id == tenant_id.value)
            if active_only:
                query = query.where(LabelModel.is_active == True)

            result = await session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, label: Label) -> Label:
        """Persist a label entity."""
        async with get_db_session() as session:
            # Check if exists
            existing = await session.get(LabelModel, label.id.value)

            if existing:
                # Update existing
                existing.name = label.name
                existing.color = label.color
                existing.description = label.description
                existing.is_active = label.is_active
            else:
                # Create new
                model = self._to_model(label)
                session.add(model)

            await session.flush()
            return label

    async def delete(self, label_id: LabelId) -> bool:
        """Delete a label."""
        async with get_db_session() as session:
            model = await session.get(LabelModel, label_id.value)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: LabelModel) -> Label:
        """Convert SQLAlchemy model to domain entity."""
        # Create entity without triggering __post_init__ events
        label = Label.__new__(Label)
        label._id = LabelId(value=model.id)
        label._tenant_id = TenantId(value=model.tenant_id)
        label._name = model.name
        label._color = model.color
        label._description = model.description or ""
        label._is_active = model.is_active
        label._created_at = model.created_at
        label._updated_at = model.updated_at
        label._events = []
        return label

    def _to_model(self, entity: Label) -> LabelModel:
        """Convert domain entity to SQLAlchemy model."""
        return LabelModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            name=entity.name,
            color=entity.color,
            description=entity.description,
            is_active=entity.is_active,
        )


class ConversationLabelRepositoryImpl(ConversationLabelRepository):
    """SQLAlchemy implementation of ConversationLabelRepository."""

    async def get_labels_for_conversation(
        self,
        conversation_id: str,
    ) -> list[Label]:
        """Get all labels applied to a conversation."""
        async with get_db_session() as session:
            result = await session.execute(
                select(LabelModel)
                .join(ConversationLabelModel, LabelModel.id == ConversationLabelModel.label_id)
                .where(ConversationLabelModel.conversation_id == conversation_id)
                .where(LabelModel.is_active == True)
            )
            models = result.scalars().all()
            return [self._label_to_entity(m) for m in models]

    async def get_conversations_for_label(
        self,
        label_id: LabelId,
        limit: int = 50,
    ) -> list[str]:
        """Get all conversations with a specific label."""
        async with get_db_session() as session:
            result = await session.execute(
                select(ConversationLabelModel.conversation_id)
                .where(ConversationLabelModel.label_id == label_id.value)
                .limit(limit)
            )
            return [row[0] for row in result.all()]

    async def add_label_to_conversation(
        self,
        conversation_label: ConversationLabel,
    ) -> ConversationLabel:
        """Apply a label to a conversation."""
        async with get_db_session() as session:
            # Check if already exists
            existing = await session.execute(
                select(ConversationLabelModel).where(
                    and_(
                        ConversationLabelModel.conversation_id == conversation_label.conversation_id,
                        ConversationLabelModel.label_id == conversation_label.label_id.value,
                    )
                )
            )
            if existing.scalar_one_or_none():
                # Already exists, return it
                return conversation_label

            # Create new
            model = self._to_model(conversation_label)
            session.add(model)
            await session.flush()
            return conversation_label

    async def remove_label_from_conversation(
        self,
        conversation_id: str,
        label_id: LabelId,
    ) -> bool:
        """Remove a label from a conversation."""
        async with get_db_session() as session:
            result = await session.execute(
                delete(ConversationLabelModel).where(
                    and_(
                        ConversationLabelModel.conversation_id == conversation_id,
                        ConversationLabelModel.label_id == label_id.value,
                    )
                )
            )
            return result.rowcount > 0

    async def remove_all_labels_from_conversation(
        self,
        conversation_id: str,
    ) -> int:
        """Remove all labels from a conversation."""
        async with get_db_session() as session:
            result = await session.execute(
                delete(ConversationLabelModel).where(
                    ConversationLabelModel.conversation_id == conversation_id
                )
            )
            return result.rowcount

    async def batch_add_labels(
        self,
        conversation_labels: list[ConversationLabel],
    ) -> list[ConversationLabel]:
        """Apply multiple labels to conversations in batch."""
        async with get_db_session() as session:
            models = [self._to_model(cl) for cl in conversation_labels]
            session.add_all(models)
            await session.flush()
            return conversation_labels

    def _label_to_entity(self, model: LabelModel) -> Label:
        """Convert LabelModel to Label entity."""
        label = Label.__new__(Label)
        label._id = LabelId(value=model.id)
        label._tenant_id = TenantId(value=model.tenant_id)
        label._name = model.name
        label._color = model.color
        label._description = model.description or ""
        label._is_active = model.is_active
        label._created_at = model.created_at
        label._updated_at = model.updated_at
        label._events = []
        return label

    def _to_model(self, entity: ConversationLabel) -> ConversationLabelModel:
        """Convert ConversationLabel entity to SQLAlchemy model."""
        return ConversationLabelModel(
            conversation_id=entity.conversation_id,
            label_id=entity.label_id.value,
            tenant_id=entity.tenant_id.value,
            applied_at=entity.applied_at,
            applied_by=entity.applied_by,
        )
