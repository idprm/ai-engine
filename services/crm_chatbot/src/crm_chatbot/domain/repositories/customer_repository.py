"""Customer repository interface."""
from abc import ABC, abstractmethod

from crm_chatbot.domain.entities import Customer
from crm_chatbot.domain.value_objects import CustomerId, TenantId, WAChatId


class CustomerRepository(ABC):
    """Abstract repository interface for Customer aggregate."""

    @abstractmethod
    async def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        """Retrieve a customer by its unique identifier.

        Args:
            customer_id: The unique identifier of the customer.

        Returns:
            The Customer aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_wa_chat_id(self, tenant_id: TenantId, wa_chat_id: WAChatId) -> Customer | None:
        """Retrieve a customer by their WhatsApp chat ID within a tenant.

        Args:
            tenant_id: The tenant the customer belongs to.
            wa_chat_id: The WhatsApp chat ID.

        Returns:
            The Customer aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_tenant(self, tenant_id: TenantId) -> list[Customer]:
        """List all customers for a tenant.

        Args:
            tenant_id: The tenant to list customers for.

        Returns:
            List of Customer aggregates.
        """
        pass

    @abstractmethod
    async def list_by_tag(self, tenant_id: TenantId, tag: str) -> list[Customer]:
        """List customers with a specific tag.

        Args:
            tenant_id: The tenant to search in.
            tag: The tag to filter by.

        Returns:
            List of Customer aggregates with the specified tag.
        """
        pass

    @abstractmethod
    async def save(self, customer: Customer) -> Customer:
        """Persist a customer aggregate.

        Args:
            customer: The customer to persist.

        Returns:
            The persisted customer.
        """
        pass

    @abstractmethod
    async def delete(self, customer_id: CustomerId) -> bool:
        """Delete a customer.

        Args:
            customer_id: The unique identifier of the customer to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
