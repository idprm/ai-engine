"""Label and ConversationLabel entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import re

from crm_chatbot.domain.events import DomainEvent
from crm_chatbot.domain.events.label_events import (
    LabelCreated,
    LabelUpdated,
    ConversationLabeled,
    ConversationUnlabeled,
)
from crm_chatbot.domain.value_objects import LabelId, TenantId


# Valid hex color pattern
HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')


@dataclass
class Label:
    """Label entity for categorizing conversations.

    Labels are used to organize and filter conversations, enabling:
    - Follow-up tracking
    - Topic categorization
    - Priority marking
    - AI-based auto-labeling
    """

    _id: LabelId
    _tenant_id: TenantId
    _name: str
    _color: str = "#3498db"  # Default blue
    _description: str = ""
    _is_active: bool = True
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Validate and emit LabelCreated event for new labels."""
        self._validate_color(self._color)
        self._validate_name(self._name)

        if not self._events:
            self._add_event(LabelCreated(
                label_id=self._id,
                tenant_id=self._tenant_id,
                name=self._name,
                color=self._color,
            ))

    @staticmethod
    def _validate_color(color: str) -> None:
        """Validate hex color format."""
        if not HEX_COLOR_PATTERN.match(color):
            raise ValueError(f"Invalid color format: {color}. Must be hex color like #3498db")

    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate label name."""
        if not name or not name.strip():
            raise ValueError("Label name cannot be empty")
        if len(name) > 100:
            raise ValueError("Label name cannot exceed 100 characters")

    @property
    def id(self) -> LabelId:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def color(self) -> str:
        return self._color

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        color: str = "#3498db",
        description: str = "",
        label_id: LabelId | None = None,
    ) -> "Label":
        """Factory method to create a new Label."""
        return cls(
            _id=label_id or LabelId.generate(),
            _tenant_id=tenant_id,
            _name=name.strip(),
            _color=color,
            _description=description,
        )

    def update_name(self, name: str) -> None:
        """Update the label name."""
        self._validate_name(name)
        self._name = name.strip()
        self._updated_at = datetime.utcnow()
        self._add_event(LabelUpdated(
            label_id=self._id,
            tenant_id=self._tenant_id,
            field="name",
        ))

    def update_color(self, color: str) -> None:
        """Update the label color."""
        self._validate_color(color)
        self._color = color
        self._updated_at = datetime.utcnow()
        self._add_event(LabelUpdated(
            label_id=self._id,
            tenant_id=self._tenant_id,
            field="color",
        ))

    def update_description(self, description: str) -> None:
        """Update the label description."""
        self._description = description
        self._updated_at = datetime.utcnow()
        self._add_event(LabelUpdated(
            label_id=self._id,
            tenant_id=self._tenant_id,
            field="description",
        ))

    def activate(self) -> None:
        """Activate the label."""
        self._is_active = True
        self._updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the label."""
        self._is_active = False
        self._updated_at = datetime.utcnow()

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert label to dictionary representation."""
        return {
            "id": str(self._id),
            "tenant_id": str(self._tenant_id),
            "name": self._name,
            "color": self._color,
            "description": self._description,
            "is_active": self._is_active,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }


@dataclass
class ConversationLabel:
    """Association entity between Conversation and Label.

    Tracks when and by whom a label was applied to a conversation.
    """

    _conversation_id: str
    _label_id: LabelId
    _tenant_id: TenantId
    _applied_at: datetime = field(default_factory=datetime.utcnow)
    _applied_by: str | None = None  # "ai" | "human" | user_id
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Emit ConversationLabeled event for new associations."""
        if not self._events:
            self._add_event(ConversationLabeled(
                conversation_id=self._conversation_id,
                label_id=self._label_id,
                tenant_id=self._tenant_id,
                applied_by=self._applied_by,
            ))

    @property
    def conversation_id(self) -> str:
        return self._conversation_id

    @property
    def label_id(self) -> LabelId:
        return self._label_id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def applied_at(self) -> datetime:
        return self._applied_at

    @property
    def applied_by(self) -> str | None:
        return self._applied_by

    @classmethod
    def create(
        cls,
        conversation_id: str,
        label_id: LabelId,
        tenant_id: TenantId,
        applied_by: str | None = None,
    ) -> "ConversationLabel":
        """Factory method to create a ConversationLabel association."""
        return cls(
            _conversation_id=conversation_id,
            _label_id=label_id,
            _tenant_id=tenant_id,
            _applied_by=applied_by,
        )

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "conversation_id": self._conversation_id,
            "label_id": str(self._label_id),
            "tenant_id": str(self._tenant_id),
            "applied_at": self._applied_at.isoformat(),
            "applied_by": self._applied_by,
        }
