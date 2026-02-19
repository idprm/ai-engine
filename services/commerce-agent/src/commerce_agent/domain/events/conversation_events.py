"""Conversation domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent
from commerce_agent.domain.value_objects import TenantId, CustomerId, ConversationState


@dataclass
class ConversationCreated(DomainEvent):
    """Event emitted when a new conversation is created."""
    conversation_id: str = ""
    tenant_id: TenantId = None
    customer_id: CustomerId = None
    event_type: str = "conversation.created"


@dataclass
class ConversationMessageAdded(DomainEvent):
    """Event emitted when a message is added to a conversation."""
    conversation_id: str = ""
    role: str = ""
    content_preview: str = ""
    event_type: str = "conversation.message_added"


@dataclass
class ConversationStateChanged(DomainEvent):
    """Event emitted when a conversation's state changes."""
    conversation_id: str = ""
    old_state: ConversationState = None
    new_state: ConversationState = None
    event_type: str = "conversation.state_changed"
