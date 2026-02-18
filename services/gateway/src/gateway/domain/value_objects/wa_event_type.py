"""WAEventType value object."""
from dataclasses import dataclass
from enum import Enum


class WAEventKind(str, Enum):
    """Supported WAHA event types."""
    MESSAGE = "message"
    MESSAGE_ANY = "message.any"
    MESSAGE_REACTION = "message.reaction"
    MESSAGE_ACK = "message.ack"
    SESSION_STATUS = "session.status"
    STATE_CHANGE = "state.change"


@dataclass(frozen=True)
class WAEventType:
    """WAHA webhook event type."""
    kind: WAEventKind

    def __post_init__(self):
        if not isinstance(self.kind, WAEventKind):
            if isinstance(self.kind, str):
                try:
                    object.__setattr__(self, "kind", WAEventKind(self.kind))
                except ValueError:
                    raise ValueError(f"Unknown WAHA event type: {self.kind}")
            else:
                raise ValueError("WAEventType must be a WAEventKind or valid string")

    @property
    def is_message(self) -> bool:
        """Check if this is a message-related event."""
        return self.kind in (
            WAEventKind.MESSAGE,
            WAEventKind.MESSAGE_ANY,
            WAEventKind.MESSAGE_REACTION,
        )

    @property
    def is_session(self) -> bool:
        """Check if this is a session-related event."""
        return self.kind in (WAEventKind.SESSION_STATUS, WAEventKind.STATE_CHANGE)

    def __str__(self) -> str:
        return self.kind.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WAEventType):
            return self.kind == other.kind
        return False

    def __hash__(self) -> int:
        return hash(self.kind)
