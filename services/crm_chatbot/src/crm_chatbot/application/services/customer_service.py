"""Customer application service."""
import logging
from typing import Any

from crm_chatbot.application.dto import CustomerDTO, UpdateCustomerDTO, CreateCustomerDTO
from crm_chatbot.domain.entities import Customer
from crm_chatbot.domain.repositories import CustomerRepository
from crm_chatbot.domain.value_objects import (
    CustomerId,
    TenantId,
    PhoneNumber,
    WAChatId,
    Money,
)

logger = logging.getLogger(__name__)


class CustomerService:
    """Application service for customer operations."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
    ):
        self._customer_repository = customer_repository

    async def get_customer(self, customer_id: str) -> CustomerDTO | None:
        """Get a customer by ID.

        Args:
            customer_id: The customer ID.

        Returns:
            CustomerDTO if found, None otherwise.
        """
        customer = await self._customer_repository.get_by_id(
            CustomerId.from_string(customer_id)
        )

        if not customer:
            return None

        return self._to_dto(customer)

    async def get_or_create_customer(
        self,
        tenant_id: str,
        phone_number: str,
        wa_chat_id: str,
        name: str | None = None,
    ) -> CustomerDTO:
        """Get existing customer or create new one.

        This is the primary method used when receiving WhatsApp messages.

        Args:
            tenant_id: The tenant ID.
            phone_number: Customer phone number.
            wa_chat_id: WhatsApp chat ID.
            name: Optional customer name.

        Returns:
            CustomerDTO for the customer.
        """
        tenant_id_vo = TenantId.from_string(tenant_id)
        phone_vo = PhoneNumber.from_raw(phone_number)
        wa_chat_id_vo = WAChatId(value=wa_chat_id)

        # Try to find existing customer
        customer = await self._customer_repository.get_by_wa_chat_id(
            tenant_id_vo,
            wa_chat_id_vo,
        )

        if not customer:
            # Create new customer
            customer = Customer.create(
                tenant_id=tenant_id_vo,
                phone_number=phone_vo,
                wa_chat_id=wa_chat_id_vo,
                name=name,
            )
            customer = await self._customer_repository.save(customer)
            logger.info(f"Created new customer: {customer.id}")

        elif name and not customer.name:
            # Update name if provided and customer doesn't have one
            customer.update_profile(name=name)
            customer = await self._customer_repository.save(customer)

        return self._to_dto(customer)

    async def update_customer(
        self,
        customer_id: str,
        dto: UpdateCustomerDTO,
    ) -> CustomerDTO:
        """Update customer profile.

        Args:
            customer_id: The customer ID.
            dto: Update data.

        Returns:
            Updated CustomerDTO.

        Raises:
            ValueError: If customer not found.
        """
        customer = await self._customer_repository.get_by_id(
            CustomerId.from_string(customer_id)
        )

        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")

        customer.update_profile(
            name=dto.name,
            email=dto.email,
            address=dto.address,
        )

        customer = await self._customer_repository.save(customer)
        return self._to_dto(customer)

    async def add_tag(self, customer_id: str, tag: str) -> CustomerDTO:
        """Add a tag to customer.

        Args:
            customer_id: The customer ID.
            tag: Tag to add.

        Returns:
            Updated CustomerDTO.
        """
        customer = await self._customer_repository.get_by_id(
            CustomerId.from_string(customer_id)
        )

        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")

        customer.add_tag(tag)
        customer = await self._customer_repository.save(customer)
        return self._to_dto(customer)

    async def remove_tag(self, customer_id: str, tag: str) -> CustomerDTO:
        """Remove a tag from customer.

        Args:
            customer_id: The customer ID.
            tag: Tag to remove.

        Returns:
            Updated CustomerDTO.
        """
        customer = await self._customer_repository.get_by_id(
            CustomerId.from_string(customer_id)
        )

        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")

        customer.remove_tag(tag)
        customer = await self._customer_repository.save(customer)
        return self._to_dto(customer)

    async def list_customers(self, tenant_id: str) -> list[CustomerDTO]:
        """List all customers for a tenant.

        Args:
            tenant_id: The tenant ID.

        Returns:
            List of CustomerDTOs.
        """
        customers = await self._customer_repository.list_by_tenant(
            TenantId.from_string(tenant_id)
        )

        return [self._to_dto(c) for c in customers]

    async def get_customer_context(self, customer_id: str) -> dict[str, Any]:
        """Get customer context for AI agent.

        Args:
            customer_id: The customer ID.

        Returns:
            Context dictionary for AI.
        """
        customer = await self._customer_repository.get_by_id(
            CustomerId.from_string(customer_id)
        )

        if not customer:
            return {}

        return {
            "customer_id": str(customer.id),
            "name": customer.name,
            "phone": str(customer.phone_number),
            "total_orders": customer.total_orders,
            "total_spent": customer.total_spent.to_float(),
            "is_vip": customer.is_vip(),
            "tags": customer.tags,
        }

    def _to_dto(self, customer: Customer) -> CustomerDTO:
        """Convert entity to DTO."""
        return CustomerDTO(
            id=str(customer.id),
            tenant_id=str(customer.tenant_id),
            phone_number=str(customer.phone_number),
            wa_chat_id=str(customer.wa_chat_id),
            name=customer.name,
            email=customer.email,
            address=customer.address,
            tags=customer.tags,
            total_orders=customer.total_orders,
            total_spent=customer.total_spent.to_float(),
            is_vip=customer.is_vip(),
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )
