"""Job aggregate root entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gateway.domain.events import JobCreated, JobCompleted, JobFailed, JobStatusChanged
from gateway.domain.value_objects import JobId, JobStatus, Prompt
from shared.events import DomainEvent


@dataclass
class Job:
    """Job aggregate root representing an AI processing job.

    This is the central aggregate for the Gateway bounded context.
    All modifications to a job's state go through this entity.
    """
    _id: JobId
    _prompt: Prompt
    _config_name: str
    _template_name: str
    _status: JobStatus = field(default=JobStatus.QUEUED)
    _result: str | None = field(default=None)
    _error: str | None = field(default=None)
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit JobCreated event for new jobs."""
        if not self._events:
            self._add_event(JobCreated(
                job_id=self._id,
                prompt=self._prompt,
                config_name=self._config_name,
                template_name=self._template_name,
            ))

    @property
    def id(self) -> JobId:
        return self._id

    @property
    def prompt(self) -> Prompt:
        return self._prompt

    @property
    def config_name(self) -> str:
        return self._config_name

    @property
    def template_name(self) -> str:
        return self._template_name

    @property
    def status(self) -> JobStatus:
        return self._status

    @property
    def result(self) -> str | None:
        return self._result

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @classmethod
    def create(
        cls,
        prompt: Prompt,
        config_name: str,
        template_name: str,
        job_id: JobId | None = None,
    ) -> "Job":
        """Factory method to create a new Job."""
        return cls(
            _id=job_id or JobId.generate(),
            _prompt=prompt,
            _config_name=config_name,
            _template_name=template_name,
        )

    def mark_processing(self) -> None:
        """Transition job to PROCESSING state."""
        if not self._status.can_transition_to(JobStatus.PROCESSING):
            raise ValueError(f"Cannot transition from {self._status} to PROCESSING")
        self._status = JobStatus.PROCESSING
        self._updated_at = datetime.utcnow()
        self._add_event(JobStatusChanged(
            job_id=self._id,
            old_status=JobStatus.QUEUED,
            new_status=JobStatus.PROCESSING,
        ))

    def complete(self, result: str) -> None:
        """Mark job as completed with result."""
        if not self._status.can_transition_to(JobStatus.COMPLETED):
            raise ValueError(f"Cannot transition from {self._status} to COMPLETED")
        self._status = JobStatus.COMPLETED
        self._result = result
        self._updated_at = datetime.utcnow()
        self._add_event(JobCompleted(
            job_id=self._id,
            result=result,
        ))

    def fail(self, error: str) -> None:
        """Mark job as failed with error message."""
        if not self._status.can_transition_to(JobStatus.FAILED):
            raise ValueError(f"Cannot transition from {self._status} to FAILED")
        self._status = JobStatus.FAILED
        self._error = error
        self._updated_at = datetime.utcnow()
        self._add_event(JobFailed(
            job_id=self._id,
            error=error,
        ))

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary representation."""
        return {
            "id": str(self._id),
            "prompt": str(self._prompt),
            "config_name": self._config_name,
            "template_name": self._template_name,
            "status": self._status.value,
            "result": self._result,
            "error": self._error,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
