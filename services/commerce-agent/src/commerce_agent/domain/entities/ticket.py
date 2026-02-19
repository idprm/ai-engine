"""Ticket, TicketBoard, and TicketTemplate entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from commerce_agent.domain.events import DomainEvent
from commerce_agent.domain.events.ticket_events import (
    TicketCreated,
    TicketStatusChanged,
    TicketPriorityChanged,
    TicketAssigned,
    TicketResolved,
    TicketClosed,
    TicketReopened,
)
from commerce_agent.domain.value_objects import TicketId, TenantId
from commerce_agent.domain.value_objects.ticket_status import TicketStatus, TicketState
from commerce_agent.domain.value_objects.ticket_priority import TicketPriority


@dataclass
class Ticket:
    """Ticket aggregate root for support ticket management.

    Tickets track customer support issues with:
    - Status workflow (open -> in_progress -> resolved -> closed)
    - Priority levels with SLA implications
    - Agent assignment
    - Conversation linking
    """

    _id: TicketId
    _tenant_id: TenantId
    _subject: str
    _description: str = ""
    _status: TicketStatus = field(default_factory=TicketStatus.open)
    _priority: TicketPriority = field(default_factory=TicketPriority.none)
    _board_id: str | None = None
    _conversation_id: str | None = None
    _customer_id: str | None = None
    _assignee_id: str | None = None
    _resolution: str | None = None
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _resolved_at: datetime | None = None
    _closed_at: datetime | None = None
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Validate and emit TicketCreated event for new tickets."""
        self._validate_subject(self._subject)

        if not self._events:
            self._add_event(TicketCreated(
                ticket_id=self._id,
                tenant_id=self._tenant_id,
                conversation_id=self._conversation_id,
                customer_id=self._customer_id,
                subject=self._subject,
                priority=self._priority,
            ))

    @staticmethod
    def _validate_subject(subject: str) -> None:
        """Validate subject."""
        if not subject or not subject.strip():
            raise ValueError("Ticket subject cannot be empty")
        if len(subject) > 500:
            raise ValueError("Subject cannot exceed 500 characters")

    @property
    def id(self) -> TicketId:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> TicketStatus:
        return self._status

    @property
    def priority(self) -> TicketPriority:
        return self._priority

    @property
    def board_id(self) -> str | None:
        return self._board_id

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id

    @property
    def customer_id(self) -> str | None:
        return self._customer_id

    @property
    def assignee_id(self) -> str | None:
        return self._assignee_id

    @property
    def resolution(self) -> str | None:
        return self._resolution

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def resolved_at(self) -> datetime | None:
        return self._resolved_at

    @property
    def closed_at(self) -> datetime | None:
        return self._closed_at

    @property
    def is_open(self) -> bool:
        return self._status.is_active()

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        subject: str,
        description: str = "",
        priority: TicketPriority | None = None,
        board_id: str | None = None,
        conversation_id: str | None = None,
        customer_id: str | None = None,
        ticket_id: TicketId | None = None,
    ) -> "Ticket":
        """Factory method to create a new Ticket."""
        return cls(
            _id=ticket_id or TicketId.generate(),
            _tenant_id=tenant_id,
            _subject=subject.strip(),
            _description=description.strip(),
            _priority=priority or TicketPriority.none(),
            _board_id=board_id,
            _conversation_id=conversation_id,
            _customer_id=customer_id,
        )

    def update_subject(self, subject: str) -> None:
        """Update the subject."""
        self._validate_subject(subject)
        self._subject = subject.strip()
        self._updated_at = datetime.utcnow()

    def update_description(self, description: str) -> None:
        """Update the description."""
        self._description = description.strip()
        self._updated_at = datetime.utcnow()

    def change_status(self, new_status: TicketStatus, changed_by: str | None = None) -> None:
        """Change ticket status with validation."""
        if not self._status.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self._status} to {new_status}")

        old_status = self._status
        self._status = new_status
        self._updated_at = datetime.utcnow()

        # Handle state-specific logic
        if new_status.state == TicketState.RESOLVED:
            self._resolved_at = datetime.utcnow()
            self._add_event(TicketResolved(
                ticket_id=self._id,
                tenant_id=self._tenant_id,
                resolved_by=changed_by,
            ))
        elif new_status.state == TicketState.CLOSED:
            self._closed_at = datetime.utcnow()
            self._add_event(TicketClosed(
                ticket_id=self._id,
                tenant_id=self._tenant_id,
                closed_by=changed_by,
            ))
        elif old_status.state == TicketState.RESOLVED and new_status.is_active():
            # Reopening
            self._resolved_at = None
            self._add_event(TicketReopened(
                ticket_id=self._id,
                tenant_id=self._tenant_id,
                reopened_by=changed_by,
            ))

        self._add_event(TicketStatusChanged(
            ticket_id=self._id,
            tenant_id=self._tenant_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
        ))

    def change_priority(self, new_priority: TicketPriority) -> None:
        """Change ticket priority."""
        if self._priority == new_priority:
            return

        old_priority = self._priority
        self._priority = new_priority
        self._updated_at = datetime.utcnow()

        self._add_event(TicketPriorityChanged(
            ticket_id=self._id,
            tenant_id=self._tenant_id,
            old_priority=old_priority,
            new_priority=new_priority,
        ))

    def assign_to(self, agent_id: str | None, assigned_by: str | None = None) -> None:
        """Assign ticket to an agent."""
        self._assignee_id = agent_id
        self._updated_at = datetime.utcnow()

        self._add_event(TicketAssigned(
            ticket_id=self._id,
            tenant_id=self._tenant_id,
            agent_id=agent_id,
            assigned_by=assigned_by,
        ))

    def unassign(self, unassigned_by: str | None = None) -> None:
        """Remove assignment from ticket."""
        self.assign_to(None, unassigned_by)

    def resolve(self, resolution: str | None = None, resolved_by: str | None = None) -> None:
        """Resolve the ticket."""
        self._resolution = resolution
        self.change_status(TicketStatus.resolved(), resolved_by)

    def close(self, closed_by: str | None = None) -> None:
        """Close the ticket."""
        self.change_status(TicketStatus.closed(), closed_by)

    def reopen(self, reopened_by: str | None = None) -> None:
        """Reopen a resolved ticket."""
        if self._status.state == TicketState.RESOLVED:
            self.change_status(TicketStatus.in_progress(), reopened_by)
        elif self._status.state == TicketState.CLOSED:
            # Closed tickets can be reopened to in_progress
            self._closed_at = None
            self.change_status(TicketStatus.in_progress(), reopened_by)

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert ticket to dictionary representation."""
        return {
            "id": str(self._id),
            "tenant_id": str(self._tenant_id),
            "subject": self._subject,
            "description": self._description,
            "status": self._status.value,
            "priority": self._priority.value,
            "board_id": self._board_id,
            "conversation_id": self._conversation_id,
            "customer_id": self._customer_id,
            "assignee_id": self._assignee_id,
            "resolution": self._resolution,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "resolved_at": self._resolved_at.isoformat() if self._resolved_at else None,
            "closed_at": self._closed_at.isoformat() if self._closed_at else None,
        }


@dataclass
class TicketBoard:
    """Entity for organizing tickets into boards/queues."""

    _id: str
    _tenant_id: TenantId
    _name: str
    _description: str = ""
    _is_default: bool = False
    _created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def id(self) -> str:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_default(self) -> bool:
        return self._is_default

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        description: str = "",
        is_default: bool = False,
        board_id: str | None = None,
    ) -> "TicketBoard":
        """Factory method to create a TicketBoard."""
        import uuid
        return cls(
            _id=board_id or str(uuid.uuid4()),
            _tenant_id=tenant_id,
            _name=name.strip(),
            _description=description.strip(),
            _is_default=is_default,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self._id,
            "tenant_id": str(self._tenant_id),
            "name": self._name,
            "description": self._description,
            "is_default": self._is_default,
            "created_at": self._created_at.isoformat(),
        }


@dataclass
class TicketTemplate:
    """Entity for predefined ticket templates."""

    _id: str
    _tenant_id: TenantId
    _name: str
    _subject_template: str = ""
    _description_template: str = ""
    _default_priority: TicketPriority = field(default_factory=TicketPriority.none)
    _created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def id(self) -> str:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def subject_template(self) -> str:
        return self._subject_template

    @property
    def description_template(self) -> str:
        return self._description_template

    @property
    def default_priority(self) -> TicketPriority:
        return self._default_priority

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        subject_template: str = "",
        description_template: str = "",
        default_priority: TicketPriority | None = None,
        template_id: str | None = None,
    ) -> "TicketTemplate":
        """Factory method to create a TicketTemplate."""
        import uuid
        return cls(
            _id=template_id or str(uuid.uuid4()),
            _tenant_id=tenant_id,
            _name=name.strip(),
            _subject_template=subject_template,
            _description_template=description_template,
            _default_priority=default_priority or TicketPriority.none(),
        )

    def render_subject(self, context: dict[str, Any] | None = None) -> str:
        """Render subject template with context."""
        if not self._subject_template:
            return ""
        try:
            return self._subject_template.format(**(context or {}))
        except KeyError:
            return self._subject_template

    def render_description(self, context: dict[str, Any] | None = None) -> str:
        """Render description template with context."""
        if not self._description_template:
            return ""
        try:
            return self._description_template.format(**(context or {}))
        except KeyError:
            return self._description_template

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self._id,
            "tenant_id": str(self._tenant_id),
            "name": self._name,
            "subject_template": self._subject_template,
            "description_template": self._description_template,
            "default_priority": self._default_priority.value,
            "created_at": self._created_at.isoformat(),
        }
