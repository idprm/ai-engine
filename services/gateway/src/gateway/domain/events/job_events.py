"""Job-related domain events."""
from dataclasses import dataclass

from gateway.domain.value_objects import JobId, JobStatus, Prompt
from shared.events import DomainEvent


@dataclass
class JobCreated(DomainEvent):
    """Event emitted when a new job is created."""
    job_id: JobId = None
    prompt: Prompt = None
    config_name: str = ""
    template_name: str = ""
    event_type: str = "job.created"


@dataclass
class JobStatusChanged(DomainEvent):
    """Event emitted when job status changes."""
    job_id: JobId = None
    old_status: JobStatus = None
    new_status: JobStatus = None
    event_type: str = "job.status_changed"


@dataclass
class JobCompleted(DomainEvent):
    """Event emitted when a job completes successfully."""
    job_id: JobId = None
    result: str = ""
    event_type: str = "job.completed"


@dataclass
class JobFailed(DomainEvent):
    """Event emitted when a job fails."""
    job_id: JobId = None
    error: str = ""
    event_type: str = "job.failed"
