"""WAMessageId value object."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WAMessageId:
    """Unique identifier for a WhatsApp message (from WAHA)."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WAMessageId must be a non-empty string")

    @classmethod
    def from_string(cls, value: str) -> "WAMessageId":
        """Create WAMessageId from string representation."""
        return cls(value)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WAMessageId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)
