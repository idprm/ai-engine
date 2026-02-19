"""QuickReply controller for API endpoints."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from crm_chatbot.application.dto import (
    QuickReplyDTO,
    CreateQuickReplyDTO,
    UpdateQuickReplyDTO,
    QuickReplyListDTO,
)
from crm_chatbot.application.services import QuickReplyService
from crm_chatbot.infrastructure.persistence import QuickReplyRepositoryImpl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants/{tenant_id}/quick-replies", tags=["Quick Replies"])


def get_quick_reply_service() -> QuickReplyService:
    """Dependency to get QuickReplyService instance."""
    return QuickReplyService(
        quick_reply_repository=QuickReplyRepositoryImpl(),
    )


@router.post("/", response_model=QuickReplyDTO, status_code=status.HTTP_201_CREATED)
async def create_quick_reply(
    tenant_id: str,
    dto: CreateQuickReplyDTO,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyDTO:
    """Create a new quick reply for a tenant.

    Args:
        tenant_id: The tenant ID.
        dto: Quick reply creation data.

    Returns:
        Created quick reply.
    """
    try:
        return await service.create_quick_reply(tenant_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=QuickReplyListDTO)
async def list_quick_replies(
    tenant_id: str,
    category: str | None = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only return active quick replies"),
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyListDTO:
    """List all quick replies for a tenant.

    Args:
        tenant_id: The tenant ID.
        category: Optional category filter.
        active_only: Whether to only return active quick replies.

    Returns:
        List of quick replies with categories.
    """
    return await service.list_quick_replies(tenant_id, category, active_only)


@router.get("/{quick_reply_id}", response_model=QuickReplyDTO)
async def get_quick_reply(
    tenant_id: str,
    quick_reply_id: str,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyDTO:
    """Get a quick reply by ID.

    Args:
        tenant_id: The tenant ID.
        quick_reply_id: The quick reply ID.

    Returns:
        Quick reply data.
    """
    quick_reply = await service.get_quick_reply(quick_reply_id)

    if not quick_reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quick reply not found: {quick_reply_id}",
        )

    return quick_reply


@router.get("/shortcut/{shortcut}", response_model=QuickReplyDTO)
async def get_by_shortcut(
    tenant_id: str,
    shortcut: str,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyDTO:
    """Get a quick reply by shortcut.

    Args:
        tenant_id: The tenant ID.
        shortcut: The shortcut code.

    Returns:
        Quick reply data.
    """
    quick_reply = await service.get_by_shortcut(tenant_id, shortcut)

    if not quick_reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quick reply not found: {shortcut}",
        )

    return quick_reply


@router.put("/{quick_reply_id}", response_model=QuickReplyDTO)
async def update_quick_reply(
    tenant_id: str,
    quick_reply_id: str,
    dto: UpdateQuickReplyDTO,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyDTO:
    """Update a quick reply.

    Args:
        tenant_id: The tenant ID.
        quick_reply_id: The quick reply ID.
        dto: Update data.

    Returns:
        Updated quick reply.
    """
    try:
        return await service.update_quick_reply(quick_reply_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{quick_reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quick_reply(
    tenant_id: str,
    quick_reply_id: str,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> None:
    """Delete a quick reply.

    Args:
        tenant_id: The tenant ID.
        quick_reply_id: The quick reply ID.
    """
    deleted = await service.delete_quick_reply(quick_reply_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quick reply not found: {quick_reply_id}",
        )


@router.post("/expand", response_model=dict[str, str])
async def expand_shortcut(
    tenant_id: str,
    message: str = Query(..., description="Message containing shortcut to expand"),
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> dict[str, str]:
    """Expand shortcuts in a message.

    Args:
        tenant_id: The tenant ID.
        message: The message to expand.

    Returns:
        Expanded message.
    """
    expanded = await service.expand_shortcut(tenant_id, message)
    return {
        "original": message,
        "expanded": expanded,
    }
