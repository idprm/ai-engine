"""Payment entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from commerce_agent.domain.events import PaymentInitiated, PaymentStatusChanged, DomainEvent
from commerce_agent.domain.value_objects import OrderId, Money, PaymentStatus


@dataclass
class Payment:
    """Payment entity representing a payment transaction.

    Payments are linked to orders and track the payment lifecycle
    with a payment gateway (Midtrans/Xendit).
    """

    _id: str                    # Payment ID from gateway
    _order_id: OrderId
    _amount: Money
    _status: PaymentStatus = PaymentStatus.PENDING
    _payment_method: str | None = None   # "bank_transfer", "ewallet", etc.
    _payment_type: str | None = None     # Specific type: "bca_va", "gopay", etc.
    _payment_url: str | None = None      # Payment URL/link
    _qr_code: str | None = None          # QR code string for some methods
    _paid_at: datetime | None = None
    _expired_at: datetime | None = None
    _metadata: dict[str, Any] = field(default_factory=dict)
    _created_at: datetime = field(default_factory=datetime.utcnow)
    _updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and emit PaymentInitiated event for new payments."""
        if not self._events:
            self._add_event(PaymentInitiated(
                payment_id=self._id,
                order_id=self._order_id,
                amount=self._amount,
            ))

    @property
    def id(self) -> str:
        return self._id

    @property
    def order_id(self) -> OrderId:
        return self._order_id

    @property
    def amount(self) -> Money:
        return self._amount

    @property
    def status(self) -> PaymentStatus:
        return self._status

    @property
    def payment_method(self) -> str | None:
        return self._payment_method

    @property
    def payment_type(self) -> str | None:
        return self._payment_type

    @property
    def payment_url(self) -> str | None:
        return self._payment_url

    @property
    def qr_code(self) -> str | None:
        return self._qr_code

    @property
    def paid_at(self) -> datetime | None:
        return self._paid_at

    @property
    def expired_at(self) -> datetime | None:
        return self._expired_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def is_pending(self) -> bool:
        return self._status in {PaymentStatus.PENDING, PaymentStatus.PENDING_PAYMENT}

    @property
    def is_paid(self) -> bool:
        return self._status == PaymentStatus.PAID

    @property
    def is_failed(self) -> bool:
        return self._status in {PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED}

    @classmethod
    def create(
        cls,
        payment_id: str,
        order_id: OrderId,
        amount: Money,
        payment_url: str | None = None,
        expired_at: datetime | None = None,
    ) -> "Payment":
        """Factory method to create a new Payment."""
        return cls(
            _id=payment_id,
            _order_id=order_id,
            _amount=amount,
            _payment_url=payment_url,
            _expired_at=expired_at,
        )

    def set_payment_details(
        self,
        payment_method: str,
        payment_type: str,
        payment_url: str | None = None,
        qr_code: str | None = None,
    ) -> None:
        """Set payment method details."""
        self._payment_method = payment_method
        self._payment_type = payment_type
        self._payment_url = payment_url
        self._qr_code = qr_code
        self._updated_at = datetime.utcnow()

    def mark_pending_payment(self) -> None:
        """Mark payment as pending customer action."""
        if self._status.can_transition_to(PaymentStatus.PENDING_PAYMENT):
            old_status = self._status
            self._status = PaymentStatus.PENDING_PAYMENT
            self._updated_at = datetime.utcnow()
            self._add_event(PaymentStatusChanged(
                payment_id=self._id,
                old_status=old_status,
                new_status=PaymentStatus.PENDING_PAYMENT,
            ))

    def mark_paid(self, paid_at: datetime | None = None) -> None:
        """Mark payment as completed."""
        if self._status.can_transition_to(PaymentStatus.PAID):
            old_status = self._status
            self._status = PaymentStatus.PAID
            self._paid_at = paid_at or datetime.utcnow()
            self._updated_at = datetime.utcnow()
            self._add_event(PaymentStatusChanged(
                payment_id=self._id,
                old_status=old_status,
                new_status=PaymentStatus.PAID,
            ))

    def mark_failed(self) -> None:
        """Mark payment as failed."""
        if self._status.can_transition_to(PaymentStatus.FAILED):
            old_status = self._status
            self._status = PaymentStatus.FAILED
            self._updated_at = datetime.utcnow()
            self._add_event(PaymentStatusChanged(
                payment_id=self._id,
                old_status=old_status,
                new_status=PaymentStatus.FAILED,
            ))

    def mark_expired(self) -> None:
        """Mark payment as expired."""
        if self._status.can_transition_to(PaymentStatus.EXPIRED):
            old_status = self._status
            self._status = PaymentStatus.EXPIRED
            self._updated_at = datetime.utcnow()
            self._add_event(PaymentStatusChanged(
                payment_id=self._id,
                old_status=old_status,
                new_status=PaymentStatus.EXPIRED,
            ))

    def mark_cancelled(self) -> None:
        """Mark payment as cancelled."""
        if self._status.can_transition_to(PaymentStatus.CANCELLED):
            old_status = self._status
            self._status = PaymentStatus.CANCELLED
            self._updated_at = datetime.utcnow()
            self._add_event(PaymentStatusChanged(
                payment_id=self._id,
                old_status=old_status,
                new_status=PaymentStatus.CANCELLED,
            ))

    def mark_refunded(self) -> None:
        """Mark payment as refunded."""
        if self._status.can_transition_to(PaymentStatus.REFUNDED):
            old_status = self._status
            self._status = PaymentStatus.REFUNDED
            self._updated_at = datetime.utcnow()
            self._add_event(PaymentStatusChanged(
                payment_id=self._id,
                old_status=old_status,
                new_status=PaymentStatus.REFUNDED,
            ))

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self._metadata[key] = value
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
        """Convert payment to dictionary representation."""
        return {
            "id": self._id,
            "order_id": str(self._order_id),
            "amount": self._amount.to_float(),
            "status": self._status.value,
            "payment_method": self._payment_method,
            "payment_type": self._payment_type,
            "payment_url": self._payment_url,
            "qr_code": self._qr_code,
            "paid_at": self._paid_at.isoformat() if self._paid_at else None,
            "expired_at": self._expired_at.isoformat() if self._expired_at else None,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
