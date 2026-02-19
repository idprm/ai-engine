"""Domain entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from messenger.domain.value_objects import WAChatId, WAMessageId, WAMessageStatus


@dataclass
class WAMessage:
    """WhatsApp outgoing message entity."""
    _id: WAMessageId
    _chat_id: WAChatId
    _text: str
    _session: str = "default"
    _reply_to: str | None = None
    _status: WAMessageStatus = WAMessageStatus.PENDING
    _job_id: str | None = None
    _source_event_id: str | None = None
    _wa_message_id: str | None = None  # Message ID from WAHA after sending
    _error: str | None = None
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _sent_at: datetime | None = None

    @property
    def id(self) -> WAMessageId:
        return self._id

    @property
    def chat_id(self) -> WAChatId:
        return self._chat_id

    @property
    def text(self) -> str:
        return self._text

    @property
    def session(self) -> str:
        return self._session

    @property
    def reply_to(self) -> str | None:
        return self._reply_to

    @property
    def status(self) -> WAMessageStatus:
        return self._status

    @property
    def job_id(self) -> str | None:
        return self._job_id

    @property
    def source_event_id(self) -> str | None:
        return self._source_event_id

    @property
    def wa_message_id(self) -> str | None:
        return self._wa_message_id

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def sent_at(self) -> datetime | None:
        return self._sent_at

    @classmethod
    def create(
        cls,
        chat_id: WAChatId,
        text: str,
        session: str = "default",
        reply_to: str | None = None,
        job_id: str | None = None,
        source_event_id: str | None = None,
        message_id: WAMessageId | None = None,
    ) -> "WAMessage":
        """Factory method to create a new WAMessage."""
        return cls(
            _id=message_id or WAMessageId(value=f"msg_{datetime.utcnow().timestamp()}"),
            _chat_id=chat_id,
            _text=text,
            _session=session,
            _reply_to=reply_to,
            _job_id=job_id,
            _source_event_id=source_event_id,
        )

    def mark_sent(self, wa_message_id: str) -> None:
        """Mark message as sent."""
        self._status = WAMessageStatus.SENT
        self._wa_message_id = wa_message_id
        self._sent_at = datetime.utcnow()

    def mark_delivered(self) -> None:
        """Mark message as delivered."""
        self._status = WAMessageStatus.DELIVERED

    def mark_failed(self, error: str) -> None:
        """Mark message as failed."""
        self._status = WAMessageStatus.FAILED
        self._error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary representation."""
        return {
            "id": str(self._id),
            "chat_id": str(self._chat_id),
            "text": self._text,
            "session": self._session,
            "reply_to": self._reply_to,
            "status": self._status.value,
            "job_id": self._job_id,
            "source_event_id": self._source_event_id,
            "wa_message_id": self._wa_message_id,
            "error": self._error,
            "created_at": self._created_at.isoformat(),
            "sent_at": self._sent_at.isoformat() if self._sent_at else None,
        }
