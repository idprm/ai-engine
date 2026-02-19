"""Payment repository interface."""
from abc import ABC, abstractmethod

from crm_chatbot.domain.entities import Payment
from crm_chatbot.domain.value_objects import OrderId, PaymentStatus


class PaymentRepository(ABC):
    """Abstract repository interface for Payment entity."""

    @abstractmethod
    async def get_by_id(self, payment_id: str) -> Payment | None:
        """Retrieve a payment by its unique identifier.

        Args:
            payment_id: The unique identifier (from payment gateway).

        Returns:
            The Payment entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_order_id(self, order_id: OrderId) -> Payment | None:
        """Get the payment for an order.

        Args:
            order_id: The order to get the payment for.

        Returns:
            The Payment if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: PaymentStatus,
        limit: int = 100,
    ) -> list[Payment]:
        """List payments by status.

        Args:
            status: The status to filter by.
            limit: Maximum number of payments to return.

        Returns:
            List of Payment entities.
        """
        pass

    @abstractmethod
    async def save(self, payment: Payment) -> Payment:
        """Persist a payment entity.

        Args:
            payment: The payment to persist.

        Returns:
            The persisted payment.
        """
        pass

    @abstractmethod
    async def delete(self, payment_id: str) -> bool:
        """Delete a payment.

        Args:
            payment_id: The unique identifier of the payment to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass
