"""LabelId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class LabelId:
    """Unique identifier for a label."""

    value: UUID

    def __post_init__(self):
        """Validate label ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("LabelId must be a UUID")

    @classmethod
    def generate(cls) -> "LabelId":
        """Generate a new unique label ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "LabelId":
        """Create LabelId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"LabelId({self.value})"
