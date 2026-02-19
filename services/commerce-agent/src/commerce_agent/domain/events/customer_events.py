"""Customer domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent
from commerce_agent.domain.value_objects import CustomerId, TenantId


@dataclass
class CustomerCreated(DomainEvent):
    """Event emitted when a new customer is created."""
    customer_id: CustomerId = None
    tenant_id: TenantId = None
    phone_number: str = ""
    event_type: str = "customer.created"


@dataclass
class CustomerUpdated(DomainEvent):
    """Event emitted when a customer is updated."""
    customer_id: CustomerId = None
    fields: list[str] = None
    event_type: str = "customer.updated"

    def __post_init__(self):
        super().__post_init__()
        if self.fields is None:
            self.fields = []
