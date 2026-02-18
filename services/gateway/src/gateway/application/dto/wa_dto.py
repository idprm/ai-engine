"""Data Transfer Objects for WhatsApp operations."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WAMessageDTO:
    """DTO for incoming WhatsApp message from webhook."""
    event_id: str
    event_type: str
    session: str
    timestamp: int
    me_id: str | None = None
    me_push_name: str | None = None
    # Message payload fields
    message_id: str | None = None
    chat_id: str | None = None
    from_me: bool = False
    text: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    # Raw payload for debugging
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_webhook(cls, data: dict[str, Any]) -> "WAMessageDTO":
        """Create DTO from WAHA webhook payload."""
        payload = data.get("payload", {})
        me = data.get("me", {})

        # Extract text from different message formats
        text = None
        if isinstance(payload.get("body"), str):
            text = payload["body"]
        elif payload.get("text"):
            text = payload["text"]

        return cls(
            event_id=data.get("id", ""),
            event_type=data.get("event", ""),
            session=data.get("session", ""),
            timestamp=data.get("timestamp", 0),
            me_id=me.get("id"),
            me_push_name=me.get("pushName"),
            message_id=payload.get("id", {}).get("id", payload.get("id", "")),
            chat_id=payload.get("from") or payload.get("to") or "",
            from_me=payload.get("fromMe", False),
            text=text,
            media_url=payload.get("mediaUrl"),
            media_type=payload.get("mediaType"),
            raw_payload=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "session": self.session,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "from_me": self.from_me,
            "text": self.text,
            "media_url": self.media_url,
            "media_type": self.media_type,
        }


@dataclass
class WAOutgoingMessageDTO:
    """DTO for outgoing WhatsApp message to be sent via waha-sender."""
    chat_id: str
    text: str
    session: str = "default"
    # Optional reply-to message ID
    reply_to: str | None = None
    # For tracking
    job_id: str | None = None
    source_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "chat_id": self.chat_id,
            "text": self.text,
            "session": self.session,
        }
        if self.reply_to:
            result["reply_to"] = self.reply_to
        if self.job_id:
            result["job_id"] = self.job_id
        if self.source_event_id:
            result["source_event_id"] = self.source_event_id
        return result
