"""Base domain event class for DDD event-driven architecture."""
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class DomainEvent(ABC):
    """Base class for all domain events.

    Domain events represent something that happened in the domain
    that other parts of the system need to be aware of.
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    event_type: str = field(default="")

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__
