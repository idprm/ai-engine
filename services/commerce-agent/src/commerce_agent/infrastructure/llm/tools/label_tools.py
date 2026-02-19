"""Label tools for CRM agent."""
import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def label_conversation(label_name: str) -> str:
    """Apply a label to the current conversation.

    Use this tool to categorize or tag the conversation for follow-up,
    priority, or topic tracking.

    Args:
        label_name: Name of the label to apply (e.g., "Follow Up", "VIP Customer",
                   "Complaint", "Product Inquiry", "Order Issue").

    Returns:
        JSON string with result.
    """
    return json.dumps({
        "label": label_name,
        "message": "Label conversation requires context - will be executed by service",
    })


@tool
async def get_available_labels() -> str:
    """Get all available labels for the tenant.

    Use this tool to see what labels can be applied to conversations.

    Returns:
        JSON string with list of available labels.
    """
    return json.dumps({
        "labels": [],
        "message": "Get labels requires tenant context - will be executed by service",
    })


@tool
async def remove_label(label_name: str) -> str:
    """Remove a label from the current conversation.

    Args:
        label_name: Name of the label to remove.

    Returns:
        JSON string with result.
    """
    return json.dumps({
        "label": label_name,
        "message": "Remove label requires context - will be executed by service",
    })


# Tool executor functions
async def execute_label_conversation(
    label_repository,
    conversation_label_repository,
    conversation_id: str,
    tenant_id: str,
    label_name: str,
    applied_by: str = "ai",
) -> dict[str, Any]:
    """Execute label_conversation tool with repository access."""
    from commerce_agent.domain.entities import ConversationLabel
    from commerce_agent.domain.value_objects import LabelId, TenantId

    tenant_id_vo = TenantId.from_string(tenant_id)

    # Find label by name
    label = await label_repository.get_by_name(tenant_id_vo, label_name)

    if not label:
        # Create label if it doesn't exist (AI can create new labels)
        from commerce_agent.domain.entities import Label
        label = Label.create(
            tenant_id=tenant_id_vo,
            name=label_name,
        )
        label = await label_repository.save(label)
        logger.info(f"Created new label: {label_name}")

    # Check if already labeled
    labels = await conversation_label_repository.get_labels_for_conversation(conversation_id)
    for existing_label in labels:
        if existing_label.name == label_name:
            return {
                "label": label_name,
                "message": f"Conversation already has label: {label_name}",
            }

    # Apply label
    conversation_label = ConversationLabel.create(
        conversation_id=conversation_id,
        label_id=label.id,
        tenant_id=tenant_id_vo,
        applied_by=applied_by,
    )

    await conversation_label_repository.add_label_to_conversation(conversation_label)

    return {
        "label": label_name,
        "label_id": str(label.id),
        "message": f"Successfully applied label: {label_name}",
    }


async def execute_get_available_labels(
    label_repository,
    tenant_id: str,
) -> dict[str, Any]:
    """Execute get_available_labels tool with repository access."""
    from commerce_agent.domain.value_objects import TenantId

    labels = await label_repository.list_by_tenant(
        TenantId.from_string(tenant_id),
        active_only=True,
    )

    return {
        "labels": [
            {
                "id": str(label.id),
                "name": label.name,
                "color": label.color,
                "description": label.description,
            }
            for label in labels
        ],
        "total": len(labels),
    }


async def execute_remove_label(
    label_repository,
    conversation_label_repository,
    conversation_id: str,
    tenant_id: str,
    label_name: str,
) -> dict[str, Any]:
    """Execute remove_label tool with repository access."""
    from commerce_agent.domain.value_objects import TenantId

    tenant_id_vo = TenantId.from_string(tenant_id)

    # Find label by name
    label = await label_repository.get_by_name(tenant_id_vo, label_name)

    if not label:
        return {
            "error": f"Label not found: {label_name}",
        }

    # Remove label
    removed = await conversation_label_repository.remove_label_from_conversation(
        conversation_id,
        label.id,
    )

    if removed:
        return {
            "label": label_name,
            "message": f"Successfully removed label: {label_name}",
        }
    else:
        return {
            "label": label_name,
            "message": f"Label was not applied to this conversation: {label_name}",
        }
