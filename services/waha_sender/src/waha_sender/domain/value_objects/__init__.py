"""Domain value objects."""
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class WAMessageId:
    """Unique identifier for a WhatsApp message."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WAMessageId must be a non-empty string")

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WAMessageId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class WAChatId:
    """WhatsApp chat identifier."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WAChatId must be a non-empty string")

    @property
    def is_group(self) -> bool:
        """Check if this is a group chat."""
        return "@g.us" in self.value

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WAChatId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


class WAMessageStatus(str, Enum):
    """WhatsApp message delivery status."""
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


@dataclass(frozen=True)
class WASession:
    """WhatsApp session information."""
    name: str

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Session name must be a non-empty string")

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WASession):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)
