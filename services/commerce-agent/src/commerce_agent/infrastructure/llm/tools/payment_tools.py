"""Payment tools for CRM agent."""
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def initiate_payment(
    order_id: str,
    payment_method: str,
) -> str:
    """Initiate payment for an order.

    Use this tool when the customer is ready to pay for their order.
    Available payment methods depend on the tenant's configuration.

    Args:
        order_id: The ID of the order to pay for.
        payment_method: Payment method type:
            - "bank_transfer": Bank transfer (VA)
            - "ewallet": E-wallet (GoPay, OVO, etc.)
            - "qris": QRIS QR code payment

    Returns:
        JSON string with payment details including payment URL or QR code.
    """
    import json
    return json.dumps({
        "payment": None,
        "message": "Initiate payment requires context - will be executed by service",
    })


@tool
async def check_payment_status(payment_id: str) -> str:
    """Check the status of a payment.

    Use this tool when the customer wants to verify their payment status.

    Args:
        payment_id: The payment ID from the payment gateway.

    Returns:
        JSON string with payment status.
    """
    import json
    return json.dumps({
        "payment": None,
        "message": "Check payment requires context - will be executed by service",
    })


# Tool executor functions
async def execute_initiate_payment(
    payment_repository,
    order_repository,
    tenant_repository,
    payment_client,  # Midtrans or Xendit client
    order_id: str,
    payment_method: str,
) -> dict[str, Any]:
    """Execute payment initiation with repository access."""
    from commerce_agent.domain.entities import Payment
    from commerce_agent.domain.value_objects import OrderId, Money

    # Get order
    order = await order_repository.get_by_id(
        OrderId.from_string(order_id)
    )

    if not order:
        return {"error": "Order not found", "order_id": order_id}

    if order.payment_status.value not in ["PENDING", "PENDING_PAYMENT"]:
        return {"error": f"Order payment status is {order.payment_status.value}"}

    # Check if payment already exists
    existing_payment = await payment_repository.get_by_order_id(order.id)
    if existing_payment and existing_payment.is_pending:
        return {
            "payment_id": existing_payment.id,
            "status": existing_payment.status.value,
            "payment_url": existing_payment.payment_url,
            "qr_code": existing_payment.qr_code,
            "expired_at": existing_payment.expired_at.isoformat() if existing_payment.expired_at else None,
            "message": "Payment already initiated",
        }

    # Create payment with gateway
    try:
        payment_result = await payment_client.create_transaction(
            order_id=str(order.id),
            amount=order.total.to_float(),
            customer_email=None,  # Could get from customer
            payment_type=payment_method,
        )
    except Exception as e:
        logger.error(f"Failed to create payment: {e}")
        return {"error": f"Failed to create payment: {str(e)}"}

    # Create payment entity
    payment = Payment.create(
        payment_id=payment_result["transaction_id"],
        order_id=order.id,
        amount=order.total,
        payment_url=payment_result.get("payment_url"),
        expired_at=payment_result.get("expiry_time"),
    )

    payment.set_payment_details(
        payment_method=payment_method,
        payment_type=payment_result.get("payment_type"),
        payment_url=payment_result.get("payment_url"),
        qr_code=payment_result.get("qr_string"),
    )

    payment.mark_pending_payment()

    await payment_repository.save(payment)

    # Update order with payment ID
    order.set_payment_id(payment.id)
    await order_repository.save(order)

    return {
        "payment_id": payment.id,
        "order_id": str(order.id),
        "amount": payment.amount.to_float(),
        "status": payment.status.value,
        "payment_method": payment.payment_method,
        "payment_url": payment.payment_url,
        "qr_code": payment.qr_code,
        "expired_at": payment.expired_at.isoformat() if payment.expired_at else None,
        "message": "Payment initiated successfully",
    }


async def execute_check_payment_status(
    payment_repository,
    order_repository,
    payment_client,
    payment_id: str,
) -> dict[str, Any]:
    """Execute payment status check with repository access."""
    # Get payment from database
    payment = await payment_repository.get_by_id(payment_id)

    if not payment:
        return {"error": "Payment not found", "payment_id": payment_id}

    # Check status with gateway
    try:
        status_result = await payment_client.check_transaction_status(payment_id)
    except Exception as e:
        logger.error(f"Failed to check payment status: {e}")
        # Return cached status
        return {
            "payment_id": payment.id,
            "status": payment.status.value,
            "cached": True,
            "message": "Using cached status - gateway check failed",
        }

    # Update payment status based on gateway response
    gateway_status = status_result.get("transaction_status", "").lower()

    if gateway_status in ["settlement", "capture"]:
        if not payment.is_paid:
            payment.mark_paid()
            await payment_repository.save(payment)

            # Update order
            from commerce_agent.domain.value_objects import OrderId
            order = await order_repository.get_by_id(payment.order_id)
            if order:
                order.mark_payment_paid()
                await order_repository.save(order)

    elif gateway_status in ["deny", "cancel", "failure"]:
        if not payment.is_failed:
            payment.mark_failed()
            await payment_repository.save(payment)

    elif gateway_status in ["expire"]:
        if not payment.is_failed:
            payment.mark_expired()
            await payment_repository.save(payment)

    return {
        "payment_id": payment.id,
        "order_id": str(payment.order_id),
        "status": payment.status.value,
        "amount": payment.amount.to_float(),
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "message": f"Payment status: {payment.status.value}",
    }
