"""SQLAlchemy implementation of OrderRepository."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from commerce_agent.domain.entities import Order, OrderItem
from commerce_agent.domain.repositories import OrderRepository
from commerce_agent.domain.value_objects import (
    OrderId,
    TenantId,
    CustomerId,
    ProductId,
    Money,
    OrderStatus,
    PaymentStatus,
)
from commerce_agent.infrastructure.persistence.database import get_db_session
from commerce_agent.infrastructure.persistence.models import OrderModel, OrderItemModel

logger = logging.getLogger(__name__)


class OrderRepositoryImpl(OrderRepository):
    """SQLAlchemy implementation of OrderRepository."""

    async def get_by_id(self, order_id: OrderId) -> Order | None:
        """Retrieve an order by its unique identifier."""
        async with get_db_session() as session:
            result = await session.execute(
                select(OrderModel).where(OrderModel.id == order_id.value)
            )
            model = result.scalar_one_or_none()
            if model:
                return self._to_entity(model, session)
            return None

    async def list_by_tenant(
        self,
        tenant_id: TenantId,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """List orders for a tenant."""
        async with get_db_session() as session:
            stmt = select(OrderModel).where(OrderModel.tenant_id == tenant_id.value)

            if status:
                stmt = stmt.where(OrderModel.status == status.value)

            stmt = stmt.order_by(OrderModel.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m, session) for m in models]

    async def list_by_customer(
        self,
        customer_id: CustomerId,
        status: OrderStatus | None = None,
        limit: int = 20,
    ) -> list[Order]:
        """List orders for a customer."""
        async with get_db_session() as session:
            stmt = select(OrderModel).where(OrderModel.customer_id == customer_id.value)

            if status:
                stmt = stmt.where(OrderModel.status == status.value)

            stmt = stmt.order_by(OrderModel.created_at.desc()).limit(limit)

            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m, session) for m in models]

    async def get_active_order_for_customer(self, customer_id: CustomerId) -> Order | None:
        """Get the active (pending) order for a customer, if any."""
        async with get_db_session() as session:
            result = await session.execute(
                select(OrderModel).where(
                    OrderModel.customer_id == customer_id.value,
                    OrderModel.status == OrderStatus.PENDING.value,
                )
            )
            model = result.scalar_one_or_none()
            if model:
                return self._to_entity(model, session)
            return None

    async def save(self, order: Order) -> Order:
        """Persist an order aggregate."""
        async with get_db_session() as session:
            existing = await session.get(OrderModel, order.id.value)

            if existing:
                existing.status = order.status.value
                existing.subtotal = order.subtotal.amount
                existing.shipping_cost = order.shipping_cost.amount
                existing.total = order.total.amount
                existing.shipping_address = order.shipping_address
                existing.payment_id = order.payment_id
                existing.payment_status = order.payment_status.value
                existing.notes = order.notes

                # Sync items
                await self._sync_items(session, existing, order.items)
            else:
                model = self._to_model(order)
                session.add(model)

            await session.flush()
            return order

    async def _sync_items(
        self,
        session: AsyncSession,
        order_model: OrderModel,
        items: list[OrderItem],
    ) -> None:
        """Sync order items."""
        # Clear existing items
        await session.execute(
            select(OrderItemModel).where(OrderItemModel.order_id == order_model.id)
        )
        for item in order_model.items:
            await session.delete(item)

        # Add new items
        for item in items:
            new_item = OrderItemModel(
                order_id=order_model.id,
                product_id=item.product_id.value,
                product_name=item.product_name,
                variant_sku=item.variant_sku,
                quantity=item.quantity,
                unit_price=item.unit_price.amount,
                subtotal=item.subtotal.amount,
            )
            session.add(new_item)

    async def delete(self, order_id: OrderId) -> bool:
        """Delete an order."""
        async with get_db_session() as session:
            model = await session.get(OrderModel, order_id.value)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: OrderModel, session: AsyncSession) -> Order:
        """Convert SQLAlchemy model to domain entity."""
        # Get items
        items = []
        for item in model.items:
            order_item = OrderItem.create(
                item_id=item.id,
                product_id=ProductId(value=item.product_id),
                product_name=item.product_name,
                variant_sku=item.variant_sku,
                quantity=item.quantity,
                unit_price=Money(amount=item.unit_price),
            )
            items.append(order_item)

        order = Order.__new__(Order)
        order._id = OrderId(value=model.id)
        order._tenant_id = TenantId(value=model.tenant_id)
        order._customer_id = CustomerId(value=model.customer_id)
        order._items = items
        order._status = OrderStatus(model.status)
        order._payment_status = PaymentStatus(model.payment_status)
        order._subtotal = Money(amount=model.subtotal)
        order._shipping_cost = Money(amount=model.shipping_cost)
        order._total = Money(amount=model.total)
        order._shipping_address = model.shipping_address
        order._payment_id = model.payment_id
        order._notes = model.notes
        order._created_at = model.created_at
        order._updated_at = model.updated_at
        order._events = []
        return order

    def _to_model(self, entity: Order) -> OrderModel:
        """Convert domain entity to SQLAlchemy model."""
        model = OrderModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            customer_id=entity.customer_id.value,
            status=entity.status.value,
            subtotal=entity.subtotal.amount,
            shipping_cost=entity.shipping_cost.amount,
            total=entity.total.amount,
            shipping_address=entity.shipping_address,
            payment_id=entity.payment_id,
            payment_status=entity.payment_status.value,
            notes=entity.notes,
        )

        # Add items
        for item in entity.items:
            model.items.append(OrderItemModel(
                product_id=item.product_id.value,
                product_name=item.product_name,
                variant_sku=item.variant_sku,
                quantity=item.quantity,
                unit_price=item.unit_price.amount,
                subtotal=item.subtotal.amount,
            ))

        return model
