"""JobId value object."""
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class JobId:
    """Unique identifier for a Job aggregate."""
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, "value", UUID(self.value))
            else:
                raise ValueError("JobId must be a UUID or valid UUID string")

    @classmethod
    def generate(cls) -> "JobId":
        """Generate a new unique JobId."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "JobId":
        """Create JobId from string representation."""
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, JobId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)
