"""Conversation and ConversationMessage entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from crm_chatbot.domain.events import (
    ConversationCreated,
    ConversationMessageAdded,
    ConversationStateChanged,
    DomainEvent,
)
from crm_chatbot.domain.value_objects import (
    ConversationState,
    CustomerId,
    TenantId,
    OrderId,
    WAChatId,
)


@dataclass
class ConversationMessage:
    """Immutable conversation message value object."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message content and role."""
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if self.role not in {"user", "assistant", "system"}:
            raise ValueError(f"Invalid message role: {self.role}")

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary representation."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_langchain_format(self) -> dict[str, str]:
        """Convert to LangChain message format."""
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class Conversation:
    """Conversation aggregate root representing a chat session.

    Conversations track the state of customer interactions and maintain
    context for the AI agent to provide relevant responses.
    """

    _id: str                  # Same as WA chat_id for simplicity
    _tenant_id: TenantId
    _customer_id: CustomerId
    _wa_chat_id: WAChatId
    _messages: list[ConversationMessage] = field(default_factory=list)
    _state: ConversationState = ConversationState.GREETING
    _context: dict[str, Any] = field(default_factory=dict)
    _current_order_id: OrderId | None = None
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit ConversationCreated event for new conversations."""
        if not self._events:
            self._add_event(ConversationCreated(
                conversation_id=self._id,
                tenant_id=self._tenant_id,
                customer_id=self._customer_id,
            ))

    @property
    def id(self) -> str:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def customer_id(self) -> CustomerId:
        return self._customer_id

    @property
    def wa_chat_id(self) -> WAChatId:
        return self._wa_chat_id

    @property
    def messages(self) -> list[ConversationMessage]:
        return self._messages.copy()

    @property
    def state(self) -> ConversationState:
        return self._state

    @property
    def context(self) -> dict[str, Any]:
        return self._context.copy()

    @property
    def current_order_id(self) -> OrderId | None:
        return self._current_order_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @classmethod
    def create(
        cls,
        conversation_id: str,
        tenant_id: TenantId,
        customer_id: CustomerId,
        wa_chat_id: WAChatId,
    ) -> "Conversation":
        """Factory method to create a new Conversation."""
        return cls(
            _id=conversation_id,
            _tenant_id=tenant_id,
            _customer_id=customer_id,
            _wa_chat_id=wa_chat_id,
        )

    def add_message(
        self,
        role: Literal["user", "assistant", "system"],
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation."""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        self._messages.append(message)
        self._updated_at = datetime.utcnow()
        self._add_event(ConversationMessageAdded(
            conversation_id=self._id,
            role=role,
            content_preview=content[:100],
        ))

    def transition_to(self, new_state: ConversationState) -> None:
        """Transition to a new conversation state."""
        if not self._state.can_transition_to(new_state):
            raise ValueError(f"Cannot transition from {self._state} to {new_state}")

        old_state = self._state
        self._state = new_state
        self._updated_at = datetime.utcnow()
        self._add_event(ConversationStateChanged(
            conversation_id=self._id,
            old_state=old_state,
            new_state=new_state,
        ))

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value for the conversation."""
        self._context[key] = value
        self._updated_at = datetime.utcnow()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value from the conversation."""
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """Clear all context values."""
        self._context.clear()
        self._updated_at = datetime.utcnow()

    def set_current_order(self, order_id: OrderId | None) -> None:
        """Set the current order being worked on."""
        self._current_order_id = order_id
        self._updated_at = datetime.utcnow()

    def get_recent_messages(self, limit: int = 10) -> list[ConversationMessage]:
        """Get the most recent messages."""
        return self._messages[-limit:] if self._messages else []

    def get_messages_for_llm(self, limit: int = 20) -> list[dict[str, str]]:
        """Get messages formatted for LLM context."""
        recent = self.get_recent_messages(limit)
        return [msg.to_langchain_format() for msg in recent]

    def get_last_user_message(self) -> ConversationMessage | None:
        """Get the most recent user message."""
        for message in reversed(self._messages):
            if message.role == "user":
                return message
        return None

    def is_empty(self) -> bool:
        """Check if conversation has no messages."""
        return len(self._messages) == 0

    def complete(self) -> None:
        """Mark conversation as completed."""
        self.transition_to(ConversationState.COMPLETED)

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert conversation to dictionary representation."""
        return {
            "id": self._id,
            "tenant_id": str(self._tenant_id),
            "customer_id": str(self._customer_id),
            "wa_chat_id": str(self._wa_chat_id),
            "messages": [msg.to_dict() for msg in self._messages],
            "state": self._state.value,
            "context": self._context,
            "current_order_id": str(self._current_order_id) if self._current_order_id else None,
            "message_count": self.message_count,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
