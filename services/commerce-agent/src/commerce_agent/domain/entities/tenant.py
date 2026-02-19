"""Tenant aggregate root entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from commerce_agent.domain.events import TenantCreated, TenantUpdated, DomainEvent
from commerce_agent.domain.value_objects import TenantId


@dataclass
class Tenant:
    """Tenant aggregate root representing a business/merchant.

    Each tenant has their own:
    - WhatsApp session (via WAHA)
    - LLM configuration
    - Product catalog
    - Customer base
    - Payment provider settings
    """

    _id: TenantId
    _name: str
    _wa_session: str           # WAHA session name
    _llm_config_name: str      # LLM config to use
    _agent_prompt: str         # Custom system prompt for AI agent
    _payment_provider: str     # "midtrans" | "xendit"
    _payment_config: dict      # Encrypted API keys (server_key, etc.)
    _business_hours: dict      # {"mon": "09:00-17:00", ...}
    _is_active: bool = True
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit TenantCreated event for new tenants."""
        if not self._events:
            self._add_event(TenantCreated(
                tenant_id=self._id,
                name=self._name,
                wa_session=self._wa_session,
            ))

    @property
    def id(self) -> TenantId:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def wa_session(self) -> str:
        return self._wa_session

    @property
    def llm_config_name(self) -> str:
        return self._llm_config_name

    @property
    def agent_prompt(self) -> str:
        return self._agent_prompt

    @property
    def payment_provider(self) -> str:
        return self._payment_provider

    @property
    def payment_config(self) -> dict:
        return self._payment_config.copy()

    @property
    def business_hours(self) -> dict:
        return self._business_hours.copy()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @classmethod
    def create(
        cls,
        name: str,
        wa_session: str,
        llm_config_name: str,
        agent_prompt: str,
        payment_provider: str,
        payment_config: dict,
        business_hours: dict | None = None,
        tenant_id: TenantId | None = None,
    ) -> "Tenant":
        """Factory method to create a new Tenant."""
        return cls(
            _id=tenant_id or TenantId.generate(),
            _name=name,
            _wa_session=wa_session,
            _llm_config_name=llm_config_name,
            _agent_prompt=agent_prompt,
            _payment_provider=payment_provider,
            _payment_config=payment_config,
            _business_hours=business_hours or {},
        )

    def update_agent_prompt(self, prompt: str) -> None:
        """Update the AI agent's system prompt."""
        self._agent_prompt = prompt
        self._updated_at = datetime.utcnow()
        self._add_event(TenantUpdated(
            tenant_id=self._id,
            field="agent_prompt",
        ))

    def update_business_hours(self, hours: dict) -> None:
        """Update business hours configuration."""
        self._business_hours = hours
        self._updated_at = datetime.utcnow()

    def update_payment_config(self, config: dict) -> None:
        """Update payment provider configuration."""
        self._payment_config = config
        self._updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the tenant."""
        self._is_active = True
        self._updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the tenant."""
        self._is_active = False
        self._updated_at = datetime.utcnow()

    def pull_events(self) -> list[DomainEvent]:
        """Pull and clear all pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list."""
        self._events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert tenant to dictionary representation."""
        return {
            "id": str(self._id),
            "name": self._name,
            "wa_session": self._wa_session,
            "llm_config_name": self._llm_config_name,
            "agent_prompt": self._agent_prompt,
            "payment_provider": self._payment_provider,
            "payment_config": self._payment_config,
            "business_hours": self._business_hours,
            "is_active": self._is_active,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
