"""Label controller for API endpoints."""
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from commerce_agent.application.dto import (
    LabelDTO,
    CreateLabelDTO,
    UpdateLabelDTO,
    ApplyLabelDTO,
    BatchApplyLabelsDTO,
    ConversationLabelsDTO,
    LabelWithConversationsDTO,
)
from commerce_agent.application.services import LabelService
from commerce_agent.domain.repositories import LabelRepository, ConversationLabelRepository
from commerce_agent.infrastructure.persistence import LabelRepositoryImpl, ConversationLabelRepositoryImpl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants/{tenant_id}/labels", tags=["Labels"])


def get_label_service() -> LabelService:
    """Dependency to get LabelService instance."""
    return LabelService(
        label_repository=LabelRepositoryImpl(),
        conversation_label_repository=ConversationLabelRepositoryImpl(),
    )


@router.post("/", response_model=LabelDTO, status_code=status.HTTP_201_CREATED)
async def create_label(
    tenant_id: str,
    dto: CreateLabelDTO,
    service: LabelService = Depends(get_label_service),
) -> LabelDTO:
    """Create a new label for a tenant.

    Args:
        tenant_id: The tenant ID.
        dto: Label creation data.

    Returns:
        Created label.
    """
    try:
        return await service.create_label(tenant_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=list[LabelDTO])
async def list_labels(
    tenant_id: str,
    active_only: bool = Query(True, description="Only return active labels"),
    service: LabelService = Depends(get_label_service),
) -> list[LabelDTO]:
    """List all labels for a tenant.

    Args:
        tenant_id: The tenant ID.
        active_only: Whether to only return active labels.

    Returns:
        List of labels.
    """
    return await service.list_labels(tenant_id, active_only)


@router.get("/with-counts", response_model=list[LabelWithConversationsDTO])
async def list_labels_with_counts(
    tenant_id: str,
    service: LabelService = Depends(get_label_service),
) -> list[LabelWithConversationsDTO]:
    """List all labels with conversation counts.

    Args:
        tenant_id: The tenant ID.

    Returns:
        List of labels with conversation counts.
    """
    return await service.get_labels_with_counts(tenant_id)


@router.get("/{label_id}", response_model=LabelDTO)
async def get_label(
    tenant_id: str,
    label_id: str,
    service: LabelService = Depends(get_label_service),
) -> LabelDTO:
    """Get a label by ID.

    Args:
        tenant_id: The tenant ID.
        label_id: The label ID.

    Returns:
        Label data.
    """
    label = await service.get_label(label_id)

    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Label not found: {label_id}",
        )

    return label


@router.put("/{label_id}", response_model=LabelDTO)
async def update_label(
    tenant_id: str,
    label_id: str,
    dto: UpdateLabelDTO,
    service: LabelService = Depends(get_label_service),
) -> LabelDTO:
    """Update a label.

    Args:
        tenant_id: The tenant ID.
        label_id: The label ID.
        dto: Update data.

    Returns:
        Updated label.
    """
    try:
        return await service.update_label(label_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(
    tenant_id: str,
    label_id: str,
    service: LabelService = Depends(get_label_service),
) -> None:
    """Delete a label.

    Args:
        tenant_id: The tenant ID.
        label_id: The label ID.
    """
    deleted = await service.delete_label(label_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Label not found: {label_id}",
        )


# Conversation label routes
conversation_router = APIRouter(
    prefix="/conversations/{conversation_id}/labels",
    tags=["Conversation Labels"],
)


@conversation_router.get("/", response_model=ConversationLabelsDTO)
async def get_conversation_labels(
    conversation_id: str,
    service: LabelService = Depends(get_label_service),
) -> ConversationLabelsDTO:
    """Get all labels for a conversation.

    Args:
        conversation_id: The conversation ID.

    Returns:
        Conversation with its labels.
    """
    return await service.get_conversation_labels(conversation_id)


@conversation_router.post("/", response_model=LabelDTO)
async def apply_label_to_conversation(
    conversation_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    dto: ApplyLabelDTO = ...,
    service: LabelService = Depends(get_label_service),
) -> LabelDTO:
    """Apply a label to a conversation.

    Args:
        conversation_id: The conversation ID.
        tenant_id: The tenant ID.
        dto: Label to apply.

    Returns:
        The applied label.
    """
    try:
        return await service.apply_label_to_conversation(
            conversation_id,
            dto,
            tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@conversation_router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_label_from_conversation(
    conversation_id: str,
    label_id: str,
    service: LabelService = Depends(get_label_service),
) -> None:
    """Remove a label from a conversation.

    Args:
        conversation_id: The conversation ID.
        label_id: The label ID.
    """
    removed = await service.remove_label_from_conversation(conversation_id, label_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found on conversation",
        )


@conversation_router.delete("/", status_code=status.HTTP_200_OK)
async def clear_conversation_labels(
    conversation_id: str,
    service: LabelService = Depends(get_label_service),
) -> dict[str, int]:
    """Remove all labels from a conversation.

    Args:
        conversation_id: The conversation ID.

    Returns:
        Number of labels removed.
    """
    count = await service.clear_conversation_labels(conversation_id)
    return {"removed_count": count}


# Batch operations router
batch_router = APIRouter(prefix="/labels/batch", tags=["Batch Label Operations"])


@batch_router.post("/apply", response_model=dict[str, Any])
async def batch_apply_labels(
    tenant_id: str = Query(..., description="Tenant ID"),
    dto: BatchApplyLabelsDTO = ...,
    service: LabelService = Depends(get_label_service),
) -> dict[str, Any]:
    """Batch apply labels to multiple conversations.

    Args:
        tenant_id: The tenant ID.
        dto: Batch apply data.

    Returns:
        Result with counts.
    """
    try:
        return await service.batch_apply_labels(dto, tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
