"""QuickReplyId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class QuickReplyId:
    """Unique identifier for a quick reply."""

    value: UUID

    def __post_init__(self):
        """Validate quick reply ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("QuickReplyId must be a UUID")

    @classmethod
    def generate(cls) -> "QuickReplyId":
        """Generate a new unique quick reply ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "QuickReplyId":
        """Create QuickReplyId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"QuickReplyId({self.value})"
