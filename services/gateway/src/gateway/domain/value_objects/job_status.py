"""JobStatus value object."""
from enum import Enum


class JobStatus(str, Enum):
    """Status of a job in the system."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def can_transition_to(self, target: "JobStatus") -> bool:
        """Check if transition to target status is valid."""
        transitions = {
            JobStatus.QUEUED: {JobStatus.PROCESSING, JobStatus.FAILED},
            JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED},
            JobStatus.COMPLETED: set(),
            JobStatus.FAILED: set(),
        }
        return target in transitions.get(self, set())
