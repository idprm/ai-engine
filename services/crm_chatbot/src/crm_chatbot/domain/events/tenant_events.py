"""Tenant domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent
from crm_chatbot.domain.value_objects import TenantId


@dataclass
class TenantCreated(DomainEvent):
    """Event emitted when a new tenant is created."""
    tenant_id: TenantId = None
    name: str = ""
    wa_session: str = ""
    event_type: str = "tenant.created"


@dataclass
class TenantUpdated(DomainEvent):
    """Event emitted when a tenant is updated."""
    tenant_id: TenantId = None
    field: str = ""
    event_type: str = "tenant.updated"
