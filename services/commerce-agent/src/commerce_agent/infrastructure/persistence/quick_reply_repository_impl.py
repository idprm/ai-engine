"""SQLAlchemy implementation of QuickReplyRepository."""
import logging
from uuid import UUID

from sqlalchemy import select, and_, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from commerce_agent.domain.entities import QuickReply
from commerce_agent.domain.repositories import QuickReplyRepository
from commerce_agent.domain.value_objects import QuickReplyId, TenantId
from commerce_agent.infrastructure.persistence.database import get_db_session
from commerce_agent.infrastructure.persistence.models import QuickReplyModel

logger = logging.getLogger(__name__)


class QuickReplyRepositoryImpl(QuickReplyRepository):
    """SQLAlchemy implementation of QuickReplyRepository."""

    async def get_by_id(self, quick_reply_id: QuickReplyId) -> QuickReply | None:
        """Retrieve a quick reply by its unique identifier."""
        async with get_db_session() as session:
            result = await session.execute(
                select(QuickReplyModel).where(QuickReplyModel.id == quick_reply_id.value)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_shortcut(self, tenant_id: TenantId, shortcut: str) -> QuickReply | None:
        """Get a quick reply by shortcut within a tenant."""
        async with get_db_session() as session:
            result = await session.execute(
                select(QuickReplyModel).where(
                    and_(
                        QuickReplyModel.tenant_id == tenant_id.value,
                        QuickReplyModel.shortcut == shortcut,
                    )
                )
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[QuickReply]:
        """List all quick replies for a tenant."""
        async with get_db_session() as session:
            query = select(QuickReplyModel).where(QuickReplyModel.tenant_id == tenant_id.value)

            if category:
                query = query.where(QuickReplyModel.category == category)

            if active_only:
                query = query.where(QuickReplyModel.is_active == True)

            result = await session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def list_categories(self, tenant_id: TenantId) -> list[str]:
        """List all categories used by a tenant."""
        async with get_db_session() as session:
            result = await session.execute(
                select(distinct(QuickReplyModel.category))
                .where(QuickReplyModel.tenant_id == tenant_id.value)
                .where(QuickReplyModel.is_active == True)
                .order_by(QuickReplyModel.category)
            )
            return [row[0] for row in result.all()]

    async def save(self, quick_reply: QuickReply) -> QuickReply:
        """Persist a quick reply entity."""
        async with get_db_session() as session:
            # Check if exists
            existing = await session.get(QuickReplyModel, quick_reply.id.value)

            if existing:
                # Update existing
                existing.shortcut = quick_reply.shortcut
                existing.content = quick_reply.content
                existing.category = quick_reply.category
                existing.is_active = quick_reply.is_active
            else:
                # Create new
                model = self._to_model(quick_reply)
                session.add(model)

            await session.flush()
            return quick_reply

    async def delete(self, quick_reply_id: QuickReplyId) -> bool:
        """Delete a quick reply."""
        async with get_db_session() as session:
            model = await session.get(QuickReplyModel, quick_reply_id.value)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: QuickReplyModel) -> QuickReply:
        """Convert SQLAlchemy model to domain entity."""
        # Create entity without triggering __post_init__ events
        quick_reply = QuickReply.__new__(QuickReply)
        quick_reply._id = QuickReplyId(value=model.id)
        quick_reply._tenant_id = TenantId(value=model.tenant_id)
        quick_reply._shortcut = model.shortcut
        quick_reply._content = model.content
        quick_reply._category = model.category
        quick_reply._is_active = model.is_active
        quick_reply._created_at = model.created_at
        quick_reply._updated_at = model.updated_at
        quick_reply._events = []
        return quick_reply

    def _to_model(self, entity: QuickReply) -> QuickReplyModel:
        """Convert domain entity to SQLAlchemy model."""
        return QuickReplyModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            shortcut=entity.shortcut,
            content=entity.content,
            category=entity.category,
            is_active=entity.is_active,
        )
