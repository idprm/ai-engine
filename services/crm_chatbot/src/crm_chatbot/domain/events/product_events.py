"""Product domain events."""
from dataclasses import dataclass

from shared.events import DomainEvent
from crm_chatbot.domain.value_objects import ProductId, TenantId


@dataclass
class ProductCreated(DomainEvent):
    """Event emitted when a new product is created."""
    product_id: ProductId = None
    tenant_id: TenantId = None
    name: str = ""
    event_type: str = "product.created"
