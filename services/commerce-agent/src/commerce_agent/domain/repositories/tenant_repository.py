"""Tenant repository interface."""
from abc import ABC, abstractmethod

from commerce_agent.domain.entities import Tenant
from commerce_agent.domain.value_objects import TenantId


class TenantRepository(ABC):
    """Abstract repository interface for Tenant aggregate."""

    @abstractmethod
    async def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve a tenant by its unique identifier.

        Args:
            tenant_id: The unique identifier of the tenant.

        Returns:
            The Tenant aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_wa_session(self, wa_session: str) -> Tenant | None:
        """Retrieve a tenant by its WhatsApp session name.

        Args:
            wa_session: The WAHA session name.

        Returns:
            The Tenant aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def save(self, tenant: Tenant) -> Tenant:
        """Persist a tenant aggregate.

        Args:
            tenant: The tenant to persist.

        Returns:
            The persisted tenant with any updates (e.g., generated ID).
        """
        pass

    @abstractmethod
    async def list_active(self) -> list[Tenant]:
        """List all active tenants.

        Returns:
            List of active Tenant aggregates.
        """
        pass

    @abstractmethod
    async def delete(self, tenant_id: TenantId) -> bool:
        """Delete a tenant.

        Args:
            tenant_id: The unique identifier of the tenant to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
