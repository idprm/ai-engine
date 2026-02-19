"""QuickReply entity for template responses."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from crm_chatbot.domain.events import DomainEvent
from crm_chatbot.domain.value_objects import QuickReplyId, TenantId


@dataclass
class QuickReply:
    """Quick Reply entity for template/saved responses.

    Quick replies allow agents to quickly respond with pre-defined
    messages, improving response time and consistency.
    """

    _id: QuickReplyId
    _tenant_id: TenantId
    _shortcut: str              # Short code to trigger the reply (e.g., "/hello")
    _content: str               # The message content
    _category: str = "general"  # Category for organization
    _is_active: bool = True
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Validate quick reply."""
        self._validate_shortcut(self._shortcut)
        self._validate_content(self._content)

    @staticmethod
    def _validate_shortcut(shortcut: str) -> None:
        """Validate shortcut format."""
        if not shortcut or not shortcut.strip():
            raise ValueError("Shortcut cannot be empty")
        if len(shortcut) > 50:
            raise ValueError("Shortcut cannot exceed 50 characters")
        # Optional: enforce format like /shortcut
        if not shortcut.startswith('/'):
            raise ValueError("Shortcut must start with '/'")

    @staticmethod
    def _validate_content(content: str) -> None:
        """Validate content."""
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

    @property
    def id(self) -> QuickReplyId:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def shortcut(self) -> str:
        return self._shortcut

    @property
    def content(self) -> str:
        return self._content

    @property
    def category(self) -> str:
        return self._category

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
        shortcut: str,
        content: str,
        category: str = "general",
        quick_reply_id: QuickReplyId | None = None,
    ) -> "QuickReply":
        """Factory method to create a new QuickReply."""
        return cls(
            _id=quick_reply_id or QuickReplyId.generate(),
            _tenant_id=tenant_id,
            _shortcut=shortcut.strip(),
            _content=content.strip(),
            _category=category.strip() if category else "general",
        )

    def update_content(self, content: str) -> None:
        """Update the content."""
        self._validate_content(content)
        self._content = content.strip()
        self._updated_at = datetime.utcnow()

    def update_category(self, category: str) -> None:
        """Update the category."""
        self._category = category.strip() if category else "general"
        self._updated_at = datetime.utcnow()

    def update_shortcut(self, shortcut: str) -> None:
        """Update the shortcut."""
        self._validate_shortcut(shortcut)
        self._shortcut = shortcut.strip()
        self._updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the quick reply."""
        self._is_active = True
        self._updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the quick reply."""
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
        """Convert quick reply to dictionary representation."""
        return {
            "id": str(self._id),
            "tenant_id": str(self._tenant_id),
            "shortcut": self._shortcut,
            "content": self._content,
            "category": self._category,
            "is_active": self._is_active,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
