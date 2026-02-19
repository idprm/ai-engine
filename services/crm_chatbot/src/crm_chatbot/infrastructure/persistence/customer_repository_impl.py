"""SQLAlchemy implementation of CustomerRepository."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crm_chatbot.domain.entities import Customer
from crm_chatbot.domain.repositories import CustomerRepository
from crm_chatbot.domain.value_objects import CustomerId, TenantId, PhoneNumber, WAChatId, Money
from crm_chatbot.infrastructure.persistence.database import get_db_session
from crm_chatbot.infrastructure.persistence.models import CustomerModel

logger = logging.getLogger(__name__)


class CustomerRepositoryImpl(CustomerRepository):
    """SQLAlchemy implementation of CustomerRepository."""

    async def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        """Retrieve a customer by its unique identifier."""
        async with get_db_session() as session:
            model = await session.get(CustomerModel, customer_id.value)
            return self._to_entity(model) if model else None

    async def get_by_wa_chat_id(self, tenant_id: TenantId, wa_chat_id: WAChatId) -> Customer | None:
        """Retrieve a customer by their WhatsApp chat ID within a tenant."""
        async with get_db_session() as session:
            result = await session.execute(
                select(CustomerModel).where(
                    CustomerModel.tenant_id == tenant_id.value,
                    CustomerModel.wa_chat_id == str(wa_chat_id),
                )
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_by_tenant(self, tenant_id: TenantId) -> list[Customer]:
        """List all customers for a tenant."""
        async with get_db_session() as session:
            result = await session.execute(
                select(CustomerModel).where(CustomerModel.tenant_id == tenant_id.value)
            )
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def list_by_tag(self, tenant_id: TenantId, tag: str) -> list[Customer]:
        """List customers with a specific tag."""
        async with get_db_session() as session:
            result = await session.execute(
                select(CustomerModel).where(
                    CustomerModel.tenant_id == tenant_id.value,
                    CustomerModel.tags.contains([tag]),
                )
            )
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, customer: Customer) -> Customer:
        """Persist a customer aggregate."""
        async with get_db_session() as session:
            existing = await session.get(CustomerModel, customer.id.value)

            if existing:
                existing.name = customer.name
                existing.email = customer.email
                existing.address = customer.address
                existing.tags = customer.tags
                existing.total_orders = customer.total_orders
                existing.total_spent = customer.total_spent.amount
            else:
                model = self._to_model(customer)
                session.add(model)

            await session.flush()
            return customer

    async def delete(self, customer_id: CustomerId) -> bool:
        """Delete a customer."""
        async with get_db_session() as session:
            model = await session.get(CustomerModel, customer_id.value)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: CustomerModel) -> Customer:
        """Convert SQLAlchemy model to domain entity."""
        customer = Customer.__new__(Customer)
        customer._id = CustomerId(value=model.id)
        customer._tenant_id = TenantId(value=model.tenant_id)
        customer._phone_number = PhoneNumber(value=model.phone_number)
        customer._wa_chat_id = WAChatId(value=model.wa_chat_id)
        customer._name = model.name
        customer._email = model.email
        customer._address = model.address
        customer._tags = model.tags or []
        customer._total_orders = model.total_orders
        customer._total_spent = Money(amount=model.total_spent)
        customer._created_at = model.created_at
        customer._updated_at = model.updated_at
        customer._events = []
        return customer

    def _to_model(self, entity: Customer) -> CustomerModel:
        """Convert domain entity to SQLAlchemy model."""
        return CustomerModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            phone_number=str(entity.phone_number),
            wa_chat_id=str(entity.wa_chat_id),
            name=entity.name,
            email=entity.email,
            address=entity.address,
            tags=entity.tags,
            total_orders=entity.total_orders,
            total_spent=entity.total_spent.amount,
        )
