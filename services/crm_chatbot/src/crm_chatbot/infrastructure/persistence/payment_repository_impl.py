"""SQLAlchemy implementation of PaymentRepository."""
import logging

from sqlalchemy import select

from crm_chatbot.domain.entities import Payment
from crm_chatbot.domain.repositories import PaymentRepository
from crm_chatbot.domain.value_objects import OrderId, Money, PaymentStatus
from crm_chatbot.infrastructure.persistence.database import get_db_session
from crm_chatbot.infrastructure.persistence.models import PaymentModel

logger = logging.getLogger(__name__)


class PaymentRepositoryImpl(PaymentRepository):
    """SQLAlchemy implementation of PaymentRepository."""

    async def get_by_id(self, payment_id: str) -> Payment | None:
        """Retrieve a payment by its unique identifier."""
        async with get_db_session() as session:
            model = await session.get(PaymentModel, payment_id)
            return self._to_entity(model) if model else None

    async def get_by_order_id(self, order_id: OrderId) -> Payment | None:
        """Get the payment for an order."""
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentModel).where(PaymentModel.order_id == order_id.value)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_by_status(
        self,
        status: PaymentStatus,
        limit: int = 100,
    ) -> list[Payment]:
        """List payments by status."""
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentModel)
                .where(PaymentModel.status == status.value)
                .limit(limit)
            )
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, payment: Payment) -> Payment:
        """Persist a payment entity."""
        async with get_db_session() as session:
            existing = await session.get(PaymentModel, payment.id)

            if existing:
                existing.status = payment.status.value
                existing.payment_method = payment.payment_method
                existing.payment_type = payment.payment_type
                existing.payment_url = payment.payment_url
                existing.qr_code = payment.qr_code
                existing.paid_at = payment.paid_at
                existing.expired_at = payment.expired_at
                existing.metadata = payment._metadata
            else:
                model = self._to_model(payment)
                session.add(model)

            await session.flush()
            return payment

    async def delete(self, payment_id: str) -> bool:
        """Delete a payment."""
        async with get_db_session() as session:
            model = await session.get(PaymentModel, payment_id)
            if model:
                await session.delete(model)
                return True
            return False

    def _to_entity(self, model: PaymentModel) -> Payment:
        """Convert SQLAlchemy model to domain entity."""
        payment = Payment.__new__(Payment)
        payment._id = model.id
        payment._order_id = OrderId(value=model.order_id)
        payment._amount = Money(amount=model.amount, currency=model.currency)
        payment._status = PaymentStatus(model.status)
        payment._payment_method = model.payment_method
        payment._payment_type = model.payment_type
        payment._payment_url = model.payment_url
        payment._qr_code = model.qr_code
        payment._paid_at = model.paid_at
        payment._expired_at = model.expired_at
        payment._metadata = model.metadata or {}
        payment._created_at = model.created_at
        payment._updated_at = model.updated_at
        payment._events = []
        return payment

    def _to_model(self, entity: Payment) -> PaymentModel:
        """Convert domain entity to SQLAlchemy model."""
        return PaymentModel(
            id=entity.id,
            order_id=entity.order_id.value,
            amount=entity.amount.amount,
            status=entity.status.value,
            payment_method=entity.payment_method,
            payment_type=entity.payment_type,
            payment_url=entity.payment_url,
            qr_code=entity.qr_code,
            paid_at=entity.paid_at,
            expired_at=entity.expired_at,
            metadata=entity._metadata,
        )
