"""Webhook controller for CRM API endpoints.

This controller handles WhatsApp and payment webhook callbacks that were migrated
from the CRM chatbot service. It publishes webhook events to the CRM worker queue
for processing.
"""
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from shared.config import get_settings
from gateway.crm.publishers import get_crm_publisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


@router.post("/whatsapp/{tenant_id}")
async def whatsapp_webhook(
    tenant_id: str,
    request: Request,
    x_waha_signature: str | None = Header(None),
) -> dict[str, Any]:
    """Handle WhatsApp webhook from WAHA.

    This endpoint receives webhook events from WAHA when new messages arrive.
    The webhook is published to the CRM task queue for processing by the worker.
    """
    try:
        payload = await request.json()

        # Add tenant_id to payload for routing
        payload["tenant_id"] = tenant_id
        payload["webhook_type"] = "whatsapp"

        # Publish to CRM worker queue
        publisher = get_crm_publisher()
        await publisher.publish_webhook_task(payload)

        logger.info(f"WhatsApp webhook published for tenant {tenant_id}")

        return {"status": "queued", "tenant_id": tenant_id}

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

    The webhook is published to the CRM task queue for processing by the worker.
    """
    try:
        payload = await request.json()

        # Create task payload
        task_payload = {
            "webhook_type": "payment",
            "provider": provider,
            "payload": payload,
        }

        # Publish to CRM worker queue
        publisher = get_crm_publisher()
        await publisher.publish_webhook_task(task_payload)

        logger.info(f"Payment webhook published for provider {provider}")

        # Return quick acknowledgment
        order_id = payload.get("order_id") or payload.get("external_id")
        return {"status": "queued", "provider": provider, "order_id": order_id}

    except Exception as e:
        logger.error(f"Payment callback error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
