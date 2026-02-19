"""Customer aggregate root entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from commerce_agent.domain.events import CustomerCreated, CustomerUpdated, DomainEvent
from commerce_agent.domain.value_objects import (
    CustomerId,
    TenantId,
    PhoneNumber,
    WAChatId,
    Money,
)


@dataclass
class Customer:
    """Customer aggregate root representing an end-user.

    Customers are associated with a specific tenant and have:
    - Contact information
    - Order history stats
    - Tags for segmentation
    """

    _id: CustomerId
    _tenant_id: TenantId
    _phone_number: PhoneNumber
    _wa_chat_id: WAChatId
    _name: str | None = None
    _email: str | None = None
    _address: dict | None = None
    _tags: list[str] = field(default_factory=list)
    _total_orders: int = 0
    _total_spent: Money = field(default_factory=lambda: Money(amount=0))
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit CustomerCreated event for new customers."""
        if not self._events:
            self._add_event(CustomerCreated(
                customer_id=self._id,
                tenant_id=self._tenant_id,
                phone_number=str(self._phone_number),
            ))

    @property
    def id(self) -> CustomerId:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def phone_number(self) -> PhoneNumber:
        return self._phone_number

    @property
    def wa_chat_id(self) -> WAChatId:
        return self._wa_chat_id

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def email(self) -> str | None:
        return self._email

    @property
    def address(self) -> dict | None:
        return self._address.copy() if self._address else None

    @property
    def tags(self) -> list[str]:
        return self._tags.copy()

    @property
    def total_orders(self) -> int:
        return self._total_orders

    @property
    def total_spent(self) -> Money:
        return self._total_spent

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        phone_number: PhoneNumber,
        wa_chat_id: WAChatId,
        name: str | None = None,
        email: str | None = None,
        address: dict | None = None,
        customer_id: CustomerId | None = None,
    ) -> "Customer":
        """Factory method to create a new Customer."""
        return cls(
            _id=customer_id or CustomerId.generate(),
            _tenant_id=tenant_id,
            _phone_number=phone_number,
            _wa_chat_id=wa_chat_id,
            _name=name,
            _email=email,
            _address=address,
        )

    def update_profile(
        self,
        name: str | None = None,
        email: str | None = None,
        address: dict | None = None,
    ) -> None:
        """Update customer profile information."""
        if name is not None:
            self._name = name
        if email is not None:
            self._email = email
        if address is not None:
            self._address = address
        self._updated_at = datetime.utcnow()
        self._add_event(CustomerUpdated(
            customer_id=self._id,
            fields=["name", "email", "address"],
        ))

    def add_tag(self, tag: str) -> None:
        """Add a tag to the customer."""
        if tag not in self._tags:
            self._tags.append(tag)
            self._updated_at = datetime.utcnow()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the customer."""
        if tag in self._tags:
            self._tags.remove(tag)
            self._updated_at = datetime.utcnow()

    def record_order(self, order_total: Money) -> None:
        """Record a completed order for stats tracking."""
        self._total_orders += 1
        self._total_spent = self._total_spent + order_total
        self._updated_at = datetime.utcnow()

    def is_vip(self) -> bool:
        """Check if customer qualifies as VIP based on spending."""
        # VIP threshold: 1 million IDR (100,000 in smallest unit)
        return self._total_spent.amount >= 100_000_00

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert customer to dictionary representation."""
        return {
            "id": str(self._id),
            "tenant_id": str(self._tenant_id),
            "phone_number": str(self._phone_number),
            "wa_chat_id": str(self._wa_chat_id),
            "name": self._name,
            "email": self._email,
            "address": self._address,
            "tags": self._tags,
            "total_orders": self._total_orders,
            "total_spent": self._total_spent.to_float(),
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
