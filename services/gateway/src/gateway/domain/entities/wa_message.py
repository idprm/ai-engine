"""WAMessage aggregate root entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gateway.domain.events import WAMessageReceived
from gateway.domain.value_objects import WAChatId, WAMessageId, WAEventType
from shared.events import DomainEvent


@dataclass
class WAMessage:
    """WAMessage aggregate root representing an incoming WhatsApp message.

    This entity is created when WAHA sends a webhook event for a new message.
    """
    _id: WAMessageId
    _chat_id: WAChatId
    _event_type: WAEventType
    _session: str
    _from_me: bool = False
    _text: str = ""
    _timestamp: int = 0
    _media_url: str | None = None
    _media_type: str | None = None
    _raw_payload: dict[str, Any] = field(default_factory=dict)
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    @property
    def id(self) -> WAMessageId:
        return self._id

    @property
    def chat_id(self) -> WAChatId:
        return self._chat_id

    @property
    def event_type(self) -> WAEventType:
        return self._event_type

    @property
    def session(self) -> str:
        return self._session

    @property
    def from_me(self) -> bool:
        return self._from_me

    @property
    def text(self) -> str:
        return self._text

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def media_url(self) -> str | None:
        return self._media_url

    @property
    def media_type(self) -> str | None:
        return self._media_type

    @property
    def raw_payload(self) -> dict[str, Any]:
        return self._raw_payload.copy()

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def from_webhook(
        cls,
        message_id: WAMessageId,
        chat_id: WAChatId,
        event_type: WAEventType,
        session: str,
        from_me: bool = False,
        text: str = "",
        timestamp: int = 0,
        media_url: str | None = None,
        media_type: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> "WAMessage":
        """Factory method to create WAMessage from webhook payload."""
        message = cls(
            _id=message_id,
            _chat_id=chat_id,
            _event_type=event_type,
            _session=session,
            _from_me=from_me,
            _text=text,
            _timestamp=timestamp,
            _media_url=media_url,
            _media_type=media_type,
            _raw_payload=raw_payload or {},
        )
        message._add_event(WAMessageReceived(
            message_id=message_id,
            chat_id=chat_id,
            event_type_enum=event_type,
            session=session,
            from_me=from_me,
            text=text,
            timestamp=timestamp,
            raw_payload=raw_payload or {},
        ))
        return message

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary representation."""
        return {
            "id": str(self._id),
            "chat_id": str(self._chat_id),
            "event_type": str(self._event_type),
            "session": self._session,
            "from_me": self._from_me,
            "text": self._text,
            "timestamp": self._timestamp,
            "media_url": self._media_url,
            "media_type": self._media_type,
            "created_at": self._created_at.isoformat(),
        }
