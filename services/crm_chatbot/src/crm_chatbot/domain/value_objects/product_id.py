"""ProductId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ProductId:
    """Unique identifier for a product."""

    value: UUID

    def __post_init__(self):
        """Validate product ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("ProductId must be a UUID")

    @classmethod
    def generate(cls) -> "ProductId":
        """Generate a new unique product ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "ProductId":
        """Create ProductId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ProductId({self.value})"
