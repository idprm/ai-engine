"""Label domain events."""
from dataclasses import dataclass
from typing import Optional

from shared.events import DomainEvent
from commerce_agent.domain.value_objects import LabelId, TenantId


@dataclass
class LabelCreated(DomainEvent):
    """Event raised when a new label is created."""

    label_id: LabelId
    tenant_id: TenantId
    name: str
    color: str


@dataclass
class LabelUpdated(DomainEvent):
    """Event raised when a label is updated."""

    label_id: LabelId
    tenant_id: TenantId
    field: str


@dataclass
class LabelDeleted(DomainEvent):
    """Event raised when a label is deleted."""

    label_id: LabelId
    tenant_id: TenantId


@dataclass
class ConversationLabeled(DomainEvent):
    """Event raised when a label is applied to a conversation."""

    conversation_id: str
    label_id: LabelId
    tenant_id: TenantId
    applied_by: Optional[str] = None  # "ai" | "human" | user_id


@dataclass
class ConversationUnlabeled(DomainEvent):
    """Event raised when a label is removed from a conversation."""

    conversation_id: str
    label_id: LabelId
    tenant_id: TenantId
