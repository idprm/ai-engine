"""WhatsApp controller handling webhook requests."""
import hashlib
import hmac
import json
import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from gateway.application.dto import WAMessageDTO, WAOutgoingMessageDTO
from gateway.application.services import WAService
from gateway.interface.schemas import (
    WAWebhookPayload,
    WAWebhookResponse,
    WASendMessageRequest,
    WASendMessageResponse,
)
from shared.config.settings import get_settings
from shared.exceptions import ValidationException

logger = logging.getLogger(__name__)


class WAController:
    """Controller for WhatsApp webhook HTTP endpoints.

    Handles WAHA webhook requests and validates HMAC signatures.
    """

    def __init__(self, wa_service: WAService, webhook_secret: str | None = None):
        self._wa_service = wa_service
        self._webhook_secret = webhook_secret

    def verify_hmac(self, payload: bytes, signature: str | None) -> bool:
        """Verify HMAC signature from WAHA.

        WAHA sends SHA512 HMAC in X-Webhook-Hmac header.

        Args:
            payload: Raw request body bytes.
            signature: HMAC signature from header.

        Returns:
            True if signature is valid or no secret configured.
        """
        if not self._webhook_secret:
            return True  # No secret configured, skip verification

        if not signature:
            logger.warning("No HMAC signature provided")
            return False

        expected = hmac.new(
            self._webhook_secret.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def handle_webhook(
        self,
        request: Request,
        payload: WAWebhookPayload,
        x_webhook_hmac: str | None = None,
    ) -> WAWebhookResponse:
        """Handle incoming WAHA webhook.

        Args:
            request: FastAPI request for raw body access.
            payload: Parsed webhook payload.
            x_webhook_hmac: HMAC signature header (optional).

        Returns:
            WAWebhookResponse acknowledging receipt.

        Raises:
            HTTPException: If HMAC verification fails or processing error.
        """
        # Verify HMAC signature
        raw_body = await request.body()
        if not self.verify_hmac(raw_body, x_webhook_hmac):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        try:
            # Convert to DTO
            dto = WAMessageDTO.from_webhook(payload.model_dump())

            # Process the webhook event
            await self._wa_service.handle_webhook_event(dto)

            return WAWebhookResponse(
                status="ok",
                event_id=payload.id,
            )

        except ValidationException as e:
            logger.warning(f"Validation error in webhook: {e}")
            # Return 200 to prevent WAHA retries for validation errors
            return WAWebhookResponse(
                status="error",
                event_id=payload.id,
            )
        except Exception as e:
            logger.exception(f"Failed to process webhook: {e}")
            # Return 500 to trigger WAHA retry
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process webhook",
            )

    async def send_message(self, request: WASendMessageRequest) -> WASendMessageResponse:
        """Queue a message for sending via waha-sender.

        Args:
            request: Message send request.

        Returns:
            WASendMessageResponse confirming queue.
        """
        try:
            dto = WAOutgoingMessageDTO(
                chat_id=request.chat_id,
                text=request.text,
                session=request.session,
                reply_to=request.reply_to,
            )

            await self._wa_service.send_message(dto)

            return WASendMessageResponse(
                status="queued",
                message=f"Message queued for sending to {request.chat_id}",
            )

        except ValidationException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": e.message, "field": e.field},
            )
        except Exception as e:
            logger.exception("Failed to queue message")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue message",
            )


def get_wa_controller() -> WAController:
    """Factory function for WAController dependency injection."""
    from gateway.main import get_wa_service
    settings = get_settings()
    return WAController(
        wa_service=get_wa_service(),
        webhook_secret=settings.waha_webhook_secret,
    )
