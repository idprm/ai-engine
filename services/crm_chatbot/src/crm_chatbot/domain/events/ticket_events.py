"""Ticket domain events."""
from dataclasses import dataclass
from typing import Optional

from shared.events import DomainEvent
from crm_chatbot.domain.value_objects import TicketId, TenantId
from crm_chatbot.domain.value_objects.ticket_status import TicketStatus
from crm_chatbot.domain.value_objects.ticket_priority import TicketPriority


@dataclass
class TicketCreated(DomainEvent):
    """Event raised when a new ticket is created."""

    ticket_id: TicketId
    tenant_id: TenantId
    conversation_id: Optional[str]
    customer_id: Optional[str]
    subject: str
    priority: TicketPriority


@dataclass
class TicketStatusChanged(DomainEvent):
    """Event raised when a ticket status changes."""

    ticket_id: TicketId
    tenant_id: TenantId
    old_status: TicketStatus
    new_status: TicketStatus
    changed_by: Optional[str] = None


@dataclass
class TicketPriorityChanged(DomainEvent):
    """Event raised when a ticket priority changes."""

    ticket_id: TicketId
    tenant_id: TenantId
    old_priority: TicketPriority
    new_priority: TicketPriority


@dataclass
class TicketAssigned(DomainEvent):
    """Event raised when a ticket is assigned to an agent."""

    ticket_id: TicketId
    tenant_id: TenantId
    agent_id: Optional[str]  # None means unassigned
    assigned_by: Optional[str] = None


@dataclass
class TicketResolved(DomainEvent):
    """Event raised when a ticket is resolved."""

    ticket_id: TicketId
    tenant_id: TenantId
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None


@dataclass
class TicketClosed(DomainEvent):
    """Event raised when a ticket is closed."""

    ticket_id: TicketId
    tenant_id: TenantId
    closed_by: Optional[str] = None


@dataclass
class TicketReopened(DomainEvent):
    """Event raised when a ticket is reopened."""

    ticket_id: TicketId
    tenant_id: TenantId
    reopened_by: Optional[str] = None
