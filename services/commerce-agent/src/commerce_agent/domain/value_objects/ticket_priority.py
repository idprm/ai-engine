"""TicketPriority value object."""
from dataclasses import dataclass
from enum import Enum


class PriorityLevel(Enum):
    """Priority levels for tickets."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class TicketPriority:
    """Value object for ticket priority with SLA implications."""

    level: PriorityLevel

    def __post_init__(self):
        """Validate priority level."""
        if not isinstance(self.level, PriorityLevel):
            raise ValueError("Invalid priority level")

    @classmethod
    def from_string(cls, value: str) -> "TicketPriority":
        """Create TicketPriority from string."""
        try:
            return cls(level=PriorityLevel(value.lower()))
        except ValueError:
            raise ValueError(f"Invalid priority: {value}")

    @classmethod
    def none(cls) -> "TicketPriority":
        """Create no priority."""
        return cls(level=PriorityLevel.NONE)

    @classmethod
    def low(cls) -> "TicketPriority":
        """Create low priority."""
        return cls(level=PriorityLevel.LOW)

    @classmethod
    def medium(cls) -> "TicketPriority":
        """Create medium priority."""
        return cls(level=PriorityLevel.MEDIUM)

    @classmethod
    def high(cls) -> "TicketPriority":
        """Create high priority."""
        return cls(level=PriorityLevel.HIGH)

    @classmethod
    def urgent(cls) -> "TicketPriority":
        """Create urgent priority."""
        return cls(level=PriorityLevel.URGENT)

    @property
    def value(self) -> str:
        """Get string value."""
        return self.level.value

    @property
    def weight(self) -> int:
        """Get numeric weight for sorting/SLA calculation."""
        weights = {
            PriorityLevel.NONE: 0,
            PriorityLevel.LOW: 1,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.HIGH: 3,
            PriorityLevel.URGENT: 4,
        }
        return weights[self.level]

    def is_higher_than(self, other: "TicketPriority") -> bool:
        """Check if this priority is higher than another."""
        return self.weight > other.weight

    def __str__(self) -> str:
        return self.level.value

    def __repr__(self) -> str:
        return f"TicketPriority({self.level.value})"

    def __lt__(self, other: "TicketPriority") -> bool:
        return self.weight < other.weight

    def __le__(self, other: "TicketPriority") -> bool:
        return self.weight <= other.weight

    def __gt__(self, other: "TicketPriority") -> bool:
        return self.weight > other.weight

    def __ge__(self, other: "TicketPriority") -> bool:
        return self.weight >= other.weight
