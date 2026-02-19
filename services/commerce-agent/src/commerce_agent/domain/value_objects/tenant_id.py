"""TenantId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TenantId:
    """Unique identifier for a tenant (business)."""

    value: UUID

    def __post_init__(self):
        """Validate tenant ID."""
        if not isinstance(self.value, UUID):
            raise ValueError("TenantId must be a UUID")

    @classmethod
    def generate(cls) -> "TenantId":
        """Generate a new unique tenant ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "TenantId":
        """Create TenantId from string representation."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"TenantId({self.value})"
