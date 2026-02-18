"""WhatsApp-related domain events."""
from dataclasses import dataclass

from gateway.domain.value_objects import WAChatId, WAMessageId, WAEventType
from shared.events import DomainEvent


@dataclass
class WAMessageReceived(DomainEvent):
    """Event emitted when a WhatsApp message is received via webhook."""
    message_id: WAMessageId = None
    chat_id: WAChatId = None
    event_type_enum: WAEventType = None
    session: str = ""
    from_me: bool = False
    text: str = ""
    timestamp: int = 0
    raw_payload: dict = None
    event_type: str = "wa.message_received"


@dataclass
class WASessionStatusChanged(DomainEvent):
    """Event emitted when WhatsApp session status changes."""
    session: str = ""
    old_status: str = ""
    new_status: str = ""
    event_type: str = "wa.session_status_changed"
