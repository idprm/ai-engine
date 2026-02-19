"""JobStatus value object."""
from enum import Enum


class JobStatus(str, Enum):
    """Status of a job in the system.

    State transitions:
    - QUEUED → PROCESSING: When worker picks up the job
    - PROCESSING → COMPLETED: On successful processing
    - PROCESSING → FAILED: On permanent failure (no retries left)
    - PROCESSING → RETRYING: On transient failure (retries remaining)
    - RETRYING → QUEUED: After delay, job is re-queued
    - RETRYING → FAILED: If max retries exceeded
    """

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

    def can_transition_to(self, target: "JobStatus") -> bool:
        """Check if transition to target status is valid."""
        transitions = {
            JobStatus.QUEUED: {JobStatus.PROCESSING, JobStatus.FAILED},
            JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.RETRYING},
            JobStatus.RETRYING: {JobStatus.QUEUED, JobStatus.FAILED},
            JobStatus.COMPLETED: set(),
            JobStatus.FAILED: set(),
        }
        return target in transitions.get(self, set())
