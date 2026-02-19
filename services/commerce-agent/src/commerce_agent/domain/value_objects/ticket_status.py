"""TicketStatus value object with transitions."""
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class TicketState(Enum):
    """Ticket states."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass(frozen=True)
class TicketStatus:
    """Value object for ticket status with valid transitions."""

    state: TicketState

    # Define valid state transitions
    VALID_TRANSITIONS: FrozenSet[tuple[TicketState, TicketState]] = frozenset({
        # From OPEN
        (TicketState.OPEN, TicketState.IN_PROGRESS),
        (TicketState.OPEN, TicketState.PENDING),
        (TicketState.OPEN, TicketState.RESOLVED),
        (TicketState.OPEN, TicketState.CLOSED),
        # From IN_PROGRESS
        (TicketState.IN_PROGRESS, TicketState.PENDING),
        (TicketState.IN_PROGRESS, TicketState.RESOLVED),
        (TicketState.IN_PROGRESS, TicketState.CLOSED),
        (TicketState.IN_PROGRESS, TicketState.OPEN),
        # From PENDING
        (TicketState.PENDING, TicketState.IN_PROGRESS),
        (TicketState.PENDING, TicketState.RESOLVED),
        (TicketState.PENDING, TicketState.CLOSED),
        # From RESOLVED
        (TicketState.RESOLVED, TicketState.CLOSED),
        (TicketState.RESOLVED, TicketState.IN_PROGRESS),  # Reopen
        (TicketState.RESOLVED, TicketState.OPEN),  # Reopen
        # CLOSED is final - no transitions allowed
    })

    def __post_init__(self):
        """Validate status state."""
        if not isinstance(self.state, TicketState):
            raise ValueError("Invalid ticket state")

    @classmethod
    def from_string(cls, value: str) -> "TicketStatus":
        """Create TicketStatus from string."""
        try:
            return cls(state=TicketState(value.lower()))
        except ValueError:
            raise ValueError(f"Invalid ticket status: {value}")

    @classmethod
    def open(cls) -> "TicketStatus":
        """Create open status."""
        return cls(state=TicketState.OPEN)

    @classmethod
    def in_progress(cls) -> "TicketStatus":
        """Create in_progress status."""
        return cls(state=TicketState.IN_PROGRESS)

    @classmethod
    def pending(cls) -> "TicketStatus":
        """Create pending status."""
        return cls(state=TicketState.PENDING)

    @classmethod
    def resolved(cls) -> "TicketStatus":
        """Create resolved status."""
        return cls(state=TicketState.RESOLVED)

    @classmethod
    def closed(cls) -> "TicketStatus":
        """Create closed status."""
        return cls(state=TicketState.CLOSED)

    @property
    def value(self) -> str:
        """Get string value."""
        return self.state.value

    def can_transition_to(self, new_status: "TicketStatus") -> bool:
        """Check if transition is valid."""
        return (self.state, new_status.state) in self.VALID_TRANSITIONS

    def is_active(self) -> bool:
        """Check if ticket is in an active state."""
        return self.state in {
            TicketState.OPEN,
            TicketState.IN_PROGRESS,
            TicketState.PENDING,
        }

    def is_final(self) -> bool:
        """Check if ticket is in a final state."""
        return self.state == TicketState.CLOSED

    def is_resolved(self) -> bool:
        """Check if ticket is resolved or closed."""
        return self.state in {TicketState.RESOLVED, TicketState.CLOSED}

    def __str__(self) -> str:
        return self.state.value

    def __repr__(self) -> str:
        return f"TicketStatus({self.state.value})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TicketStatus):
            return self.state == other.state
        return False

    def __hash__(self) -> int:
        return hash(self.state)
