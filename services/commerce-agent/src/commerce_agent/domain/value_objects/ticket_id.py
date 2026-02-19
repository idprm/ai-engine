"""TicketId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TicketId:
    """Unique identifier for a ticket."""

    value: UUID

    def __post_init__(self):
        """Validate ticket ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("TicketId must be a UUID")

    @classmethod
    def generate(cls) -> "TicketId":
        """Generate a new unique ticket ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "TicketId":
        """Create TicketId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"TicketId({self.value})"
