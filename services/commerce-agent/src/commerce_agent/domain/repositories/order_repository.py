"""Order repository interface."""
from abc import ABC, abstractmethod

from commerce_agent.domain.entities import Order
from commerce_agent.domain.value_objects import OrderId, TenantId, CustomerId, OrderStatus


class OrderRepository(ABC):
    """Abstract repository interface for Order aggregate."""

    @abstractmethod
    async def get_by_id(self, order_id: OrderId) -> Order | None:
        """Retrieve an order by its unique identifier.

        Args:
            order_id: The unique identifier of the order.

        Returns:
            The Order aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """List orders for a tenant.

        Args:
            tenant_id: The tenant to list orders for.
            status: Optional status filter.
            limit: Maximum number of orders to return.
            offset: Number of orders to skip.

        Returns:
            List of Order aggregates.
        """
        pass

    @abstractmethod
    async def list_by_customer(
        self,
        customer_id: CustomerId,
        status: OrderStatus | None = None,
        limit: int = 20,
    ) -> list[Order]:
        """List orders for a customer.

        Args:
            customer_id: The customer to list orders for.
            status: Optional status filter.
            limit: Maximum number of orders to return.

        Returns:
            List of Order aggregates.
        """
        pass

    @abstractmethod
    async def get_active_order_for_customer(self, customer_id: CustomerId) -> Order | None:
        """Get the active (pending) order for a customer, if any.

        Args:
            customer_id: The customer to check.

        Returns:
            The active Order if found, None otherwise.
        """
        pass

    @abstractmethod
    async def save(self, order: Order) -> Order:
        """Persist an order aggregate.

        Args:
            order: The order to persist.

        Returns:
            The persisted order.
        """
        pass

    @abstractmethod
    async def delete(self, order_id: OrderId) -> bool:
        """Delete an order.

        Args:
            order_id: The unique identifier of the order to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
