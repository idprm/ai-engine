"""QuickReply application service."""
import logging
from typing import Any

from commerce_agent.application.dto.quick_reply_dto import (
    QuickReplyDTO,
    CreateQuickReplyDTO,
    UpdateQuickReplyDTO,
    QuickReplyListDTO,
)
from commerce_agent.domain.entities import QuickReply
from commerce_agent.domain.repositories import QuickReplyRepository
from commerce_agent.domain.value_objects import QuickReplyId, TenantId

logger = logging.getLogger(__name__)


class QuickReplyService:
    """Application service for quick reply operations."""

    def __init__(
        self,
        quick_reply_repository: QuickReplyRepository,
    ):
        self._quick_reply_repository = quick_reply_repository

    async def get_quick_reply(self, quick_reply_id: str) -> QuickReplyDTO | None:
        """Get a quick reply by ID.

        Args:
            quick_reply_id: The quick reply ID.

        Returns:
            QuickReplyDTO if found, None otherwise.
        """
        quick_reply = await self._quick_reply_repository.get_by_id(
            QuickReplyId.from_string(quick_reply_id)
        )

        if not quick_reply:
            return None

        return self._to_dto(quick_reply)

    async def get_by_shortcut(self, tenant_id: str, shortcut: str) -> QuickReplyDTO | None:
        """Get a quick reply by shortcut.

        Args:
            tenant_id: The tenant ID.
            shortcut: The shortcut code.

        Returns:
            QuickReplyDTO if found, None otherwise.
        """
        quick_reply = await self._quick_reply_repository.get_by_shortcut(
            TenantId.from_string(tenant_id),
            shortcut,
        )

        if not quick_reply:
            return None

        return self._to_dto(quick_reply)

    async def list_quick_replies(
        self,
        tenant_id: str,
        category: str | None = None,
        active_only: bool = True,
    ) -> QuickReplyListDTO:
        """List all quick replies for a tenant.

        Args:
            tenant_id: The tenant ID.
            category: Optional category filter.
            active_only: Whether to only return active quick replies.

        Returns:
            QuickReplyListDTO with quick replies and categories.
        """
        tenant_id_vo = TenantId.from_string(tenant_id)

        quick_replies = await self._quick_reply_repository.list_by_tenant(
            tenant_id_vo,
            category=category,
            active_only=active_only,
        )

        categories = await self._quick_reply_repository.list_categories(tenant_id_vo)

        return QuickReplyListDTO(
            quick_replies=[self._to_dto(qr) for qr in quick_replies],
            categories=categories,
            total=len(quick_replies),
        )

    async def create_quick_reply(
        self,
        tenant_id: str,
        dto: CreateQuickReplyDTO,
    ) -> QuickReplyDTO:
        """Create a new quick reply.

        Args:
            tenant_id: The tenant ID.
            dto: Quick reply creation data.

        Returns:
            Created QuickReplyDTO.

        Raises:
            ValueError: If shortcut already exists or invalid format.
        """
        tenant_id_vo = TenantId.from_string(tenant_id)

        # Validate shortcut format
        if not dto.shortcut.startswith('/'):
            raise ValueError("Shortcut must start with '/'")

        # Check if shortcut already exists
        existing = await self._quick_reply_repository.get_by_shortcut(
            tenant_id_vo,
            dto.shortcut,
        )
        if existing:
            raise ValueError(f"Quick reply with shortcut '{dto.shortcut}' already exists")

        quick_reply = QuickReply.create(
            tenant_id=tenant_id_vo,
            shortcut=dto.shortcut,
            content=dto.content,
            category=dto.category,
        )

        quick_reply = await self._quick_reply_repository.save(quick_reply)
        logger.info(f"Created quick reply: {quick_reply.id} for tenant: {tenant_id}")

        return self._to_dto(quick_reply)

    async def update_quick_reply(
        self,
        quick_reply_id: str,
        dto: UpdateQuickReplyDTO,
    ) -> QuickReplyDTO:
        """Update a quick reply.

        Args:
            quick_reply_id: The quick reply ID.
            dto: Update data.

        Returns:
            Updated QuickReplyDTO.

        Raises:
            ValueError: If quick reply not found or shortcut conflict.
        """
        quick_reply = await self._quick_reply_repository.get_by_id(
            QuickReplyId.from_string(quick_reply_id)
        )

        if not quick_reply:
            raise ValueError(f"Quick reply not found: {quick_reply_id}")

        if dto.shortcut is not None:
            # Check for shortcut conflict
            existing = await self._quick_reply_repository.get_by_shortcut(
                quick_reply.tenant_id,
                dto.shortcut,
            )
            if existing and str(existing.id) != quick_reply_id:
                raise ValueError(f"Quick reply with shortcut '{dto.shortcut}' already exists")
            quick_reply.update_shortcut(dto.shortcut)

        if dto.content is not None:
            quick_reply.update_content(dto.content)

        if dto.category is not None:
            quick_reply.update_category(dto.category)

        if dto.is_active is not None:
            if dto.is_active:
                quick_reply.activate()
            else:
                quick_reply.deactivate()

        quick_reply = await self._quick_reply_repository.save(quick_reply)
        return self._to_dto(quick_reply)

    async def delete_quick_reply(self, quick_reply_id: str) -> bool:
        """Delete a quick reply.

        Args:
            quick_reply_id: The quick reply ID.

        Returns:
            True if deleted, False if not found.
        """
        deleted = await self._quick_reply_repository.delete(
            QuickReplyId.from_string(quick_reply_id)
        )

        if deleted:
            logger.info(f"Deleted quick reply: {quick_reply_id}")

        return deleted

    async def expand_shortcut(
        self,
        tenant_id: str,
        message: str,
    ) -> str:
        """Expand shortcuts in a message.

        Args:
            tenant_id: The tenant ID.
            message: The message potentially containing shortcuts.

        Returns:
            Message with shortcuts expanded, or original if no shortcut found.
        """
        # Check if message starts with a shortcut pattern
        words = message.strip().split()
        if not words or not words[0].startswith('/'):
            return message

        shortcut = words[0]

        quick_reply = await self._quick_reply_repository.get_by_shortcut(
            TenantId.from_string(tenant_id),
            shortcut,
        )

        if quick_reply:
            # Return the content, optionally with remaining words appended
            remaining = ' '.join(words[1:])
            if remaining:
                return f"{quick_reply.content} {remaining}"
            return quick_reply.content

        return message

    def _to_dto(self, quick_reply: QuickReply) -> QuickReplyDTO:
        """Convert entity to DTO."""
        return QuickReplyDTO(
            id=str(quick_reply.id),
            tenant_id=str(quick_reply.tenant_id),
            shortcut=quick_reply.shortcut,
            content=quick_reply.content,
            category=quick_reply.category,
            is_active=quick_reply.is_active,
            created_at=quick_reply.created_at,
            updated_at=quick_reply.updated_at,
        )
