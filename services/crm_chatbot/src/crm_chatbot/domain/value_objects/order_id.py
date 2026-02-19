"""OrderId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class OrderId:
    """Unique identifier for an order."""

    value: UUID

    def __post_init__(self):
        """Validate order ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("OrderId must be a UUID")

    @classmethod
    def generate(cls) -> "OrderId":
        """Generate a new unique order ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "OrderId":
        """Create OrderId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"OrderId({self.value})"
