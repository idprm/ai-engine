"""QuickReply controller for CRM API endpoints.

This controller handles quick reply management operations that were migrated
from the CRM chatbot service.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from commerce_agent.application.dto import (
    QuickReplyDTO,
    CreateQuickReplyDTO,
    UpdateQuickReplyDTO,
    QuickReplyListDTO,
)
from commerce_agent.application.services import QuickReplyService
from gateway.crm.dependencies import get_quick_reply_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants/{tenant_id}/quick-replies", tags=["Quick Replies"])


@router.post("/", response_model=QuickReplyDTO, status_code=status.HTTP_201_CREATED)
async def create_quick_reply(
    tenant_id: str,
    dto: CreateQuickReplyDTO,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyDTO:
    """Create a new quick reply for a tenant."""
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
    """List all quick replies for a tenant."""
    return await service.list_quick_replies(tenant_id, category, active_only)


@router.get("/{quick_reply_id}", response_model=QuickReplyDTO)
async def get_quick_reply(
    tenant_id: str,
    quick_reply_id: str,
    service: QuickReplyService = Depends(get_quick_reply_service),
) -> QuickReplyDTO:
    """Get a quick reply by ID."""
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
    """Get a quick reply by shortcut."""
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
    """Update a quick reply."""
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
    """Delete a quick reply."""
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
    """Expand shortcuts in a message."""
    expanded = await service.expand_shortcut(tenant_id, message)
    return {
        "original": message,
        "expanded": expanded,
    }
