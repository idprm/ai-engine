"""OrderStatus and PaymentStatus value objects."""
from enum import Enum


class OrderStatus(str, Enum):
    """Status of an order with valid transitions."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

    def can_transition_to(self, target: "OrderStatus") -> bool:
        """Check if transition to target status is valid.

        Transition rules:
        - PENDING -> CONFIRMED, CANCELLED
        - CONFIRMED -> PROCESSING, CANCELLED
        - PROCESSING -> SHIPPED, CANCELLED
        - SHIPPED -> DELIVERED
        - DELIVERED -> (terminal)
        - CANCELLED -> (terminal)
        """
        transitions = {
            OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
            OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
            OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
            OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
            OrderStatus.DELIVERED: set(),
            OrderStatus.CANCELLED: set(),
        }
        return target in transitions.get(self, set())


class PaymentStatus(str, Enum):
    """Status of a payment."""

    PENDING = "PENDING"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    def can_transition_to(self, target: "PaymentStatus") -> bool:
        """Check if transition to target status is valid."""
        transitions = {
            PaymentStatus.PENDING: {PaymentStatus.PENDING_PAYMENT, PaymentStatus.CANCELLED},
            PaymentStatus.PENDING_PAYMENT: {PaymentStatus.PAID, PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED},
            PaymentStatus.PAID: {PaymentStatus.REFUNDED},
            PaymentStatus.FAILED: set(),
            PaymentStatus.REFUNDED: set(),
            PaymentStatus.CANCELLED: set(),
            PaymentStatus.EXPIRED: set(),
        }
        return target in transitions.get(self, set())
