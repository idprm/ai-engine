"""Processing-related domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent


@dataclass
class ProcessingStarted(DomainEvent):
    """Event emitted when job processing starts."""
    job_id: str = ""
    config_name: str = ""
    template_name: str = ""
    event_type: str = "processing.started"


@dataclass
class ProcessingCompleted(DomainEvent):
    """Event emitted when job processing completes."""
    job_id: str = ""
    result: str = ""
    tokens_used: int = 0
    event_type: str = "processing.completed"


@dataclass
class ProcessingFailed(DomainEvent):
    """Event emitted when job processing fails."""
    job_id: str = ""
    error: str = ""
    event_type: str = "processing.failed"
