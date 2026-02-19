"""CustomerId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CustomerId:
    """Unique identifier for a customer."""

    value: UUID

    def __post_init__(self):
        """Validate customer ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("CustomerId must be a UUID")

    @classmethod
    def generate(cls) -> "CustomerId":
        """Generate a new unique customer ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "CustomerId":
        """Create CustomerId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"CustomerId({self.value})"
