"""Webhook controller for WhatsApp and payment callbacks."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from commerce_agent.application.handlers import WAMessageHandler
from shared.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


class WebhookController:
    """Controller for webhook endpoints."""

    def __init__(self, wa_message_handler: WAMessageHandler):
        self._wa_message_handler = wa_message_handler

    def get_router(self) -> APIRouter:
        return router


@router.post("/whatsapp/{tenant_id}")
async def whatsapp_webhook(
    tenant_id: str,
    request: Request,
    wa_message_handler: WAMessageHandler = Depends(),
    x_waha_signature: str | None = Header(None),
) -> dict[str, Any]:
    """Handle WhatsApp webhook from WAHA.

    This endpoint receives webhook events from WAHA when new messages arrive.
    """
    try:
        payload = await request.json()

        # Add tenant_id to payload for routing
        payload["tenant_id"] = tenant_id

        # Handle the webhook
        result = await wa_message_handler.handle_webhook(payload)

        return result

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/whatsapp/{tenant_id}")
async def whatsapp_webhook_verify(
    tenant_id: str,
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
) -> Any:
    """Verify WhatsApp webhook (for Meta Cloud API compatibility)."""
    settings = get_settings()

    # For WAHA webhooks, we don't need verification
    # This is kept for compatibility with Meta's webhook verification
    if hub_mode == "subscribe" and hub_challenge:
        # In production, verify the token
        # For now, just return the challenge
        return int(hub_challenge)

    return {"status": "ok", "tenant_id": tenant_id}


@router.post("/payments/{provider}")
async def payment_callback(
    provider: str,
    request: Request,
) -> dict[str, Any]:
    """Handle payment gateway callbacks.

    Supported providers: midtrans, xendit
    """
    try:
        if provider == "midtrans":
            return await _handle_midtrans_callback(request)
        elif provider == "xendit":
            return await _handle_xendit_callback(request)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown payment provider: {provider}",
            )

    except Exception as e:
        logger.error(f"Payment callback error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


async def _handle_midtrans_callback(request: Request) -> dict[str, Any]:
    """Handle Midtrans payment callback."""
    payload = await request.json()

    # Extract notification data
    order_id = payload.get("order_id")
    transaction_status = payload.get("transaction_status")
    payment_type = payload.get("payment_type")
    transaction_id = payload.get("transaction_id")

    logger.info(
        f"Midtrans callback: order={order_id}, status={transaction_status}, "
        f"type={payment_type}, tx_id={transaction_id}"
    )

    # TODO: Verify signature and update payment status
    # This would typically:
    # 1. Verify the signature using server key
    # 2. Update payment status in database
    # 3. Update order status accordingly
    # 4. Send notification to customer

    return {"status": "ok", "order_id": order_id}


async def _handle_xendit_callback(request: Request) -> dict[str, Any]:
    """Handle Xendit payment callback."""
    payload = await request.json()

    # Extract callback data
    external_id = payload.get("external_id")
    status = payload.get("status")
    payment_method = payload.get("payment_method")
    amount = payload.get("amount")

    logger.info(
        f"Xendit callback: external_id={external_id}, status={status}, "
        f"method={payment_method}, amount={amount}"
    )

    # TODO: Verify callback token and update payment status
    # Similar to Midtrans handling

    return {"status": "ok", "external_id": external_id}
