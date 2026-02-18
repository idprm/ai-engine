"""Application DTOs."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WAMessageDTO:
    """DTO for outgoing WhatsApp message."""
    chat_id: str
    text: str
    session: str = "default"
    reply_to: str | None = None
    job_id: str | None = None
    source_event_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WAMessageDTO":
        """Create DTO from dictionary."""
        return cls(
            chat_id=data.get("chat_id", ""),
            text=data.get("text", ""),
            session=data.get("session", "default"),
            reply_to=data.get("reply_to"),
            job_id=data.get("job_id"),
            source_event_id=data.get("source_event_id"),
        )
