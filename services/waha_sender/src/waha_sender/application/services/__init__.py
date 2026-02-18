"""Application services."""
import logging
from typing import Protocol

from waha_sender.application.dto import WAMessageDTO
from waha_sender.domain.entities import WAMessage
from waha_sender.domain.value_objects import WAChatId, WAMessageId

logger = logging.getLogger(__name__)


class WAHAClient(Protocol):
    """Protocol for WAHA API client."""

    async def send_text(
        self,
        chat_id: str,
        text: str,
        session: str,
        reply_to: str | None = None,
    ) -> dict:
        """Send a text message via WAHA."""
        ...


class CacheClient(Protocol):
    """Protocol for cache operations."""

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...


class WASenderService:
    """Application service for sending WhatsApp messages.

    Consumes messages from the queue and sends them via WAHA API.
    """

    def __init__(
        self,
        waha_client: WAHAClient,
        cache_client: CacheClient | None = None,
        cache_ttl: int = 3600,
    ):
        self._waha_client = waha_client
        self._cache_client = cache_client
        self._cache_ttl = cache_ttl

    async def send_message(self, dto: WAMessageDTO) -> WAMessage:
        """Send a WhatsApp message.

        Args:
            dto: Message data to send.

        Returns:
            WAMessage entity with updated status.
        """
        # Create domain entity
        chat_id = WAChatId(value=dto.chat_id)
        message = WAMessage.create(
            chat_id=chat_id,
            text=dto.text,
            session=dto.session,
            reply_to=dto.reply_to,
            job_id=dto.job_id,
            source_event_id=dto.source_event_id,
        )

        try:
            # Send via WAHA API
            logger.info(f"Sending message to {dto.chat_id} via session {dto.session}")
            result = await self._waha_client.send_text(
                chat_id=dto.chat_id,
                text=dto.text,
                session=dto.session,
                reply_to=dto.reply_to,
            )

            # Extract message ID from WAHA response
            wa_message_id = result.get("id") or result.get("messageId")
            if wa_message_id:
                message.mark_sent(wa_message_id)
            else:
                message.mark_sent("unknown")

            logger.info(f"Message sent successfully: {message.wa_message_id}")

            # Cache the message status if cache available
            if self._cache_client and dto.job_id:
                await self._update_job_status(dto.job_id, "WA_SENT", message.wa_message_id)

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            message.mark_failed(str(e))

            # Update job status if cache available
            if self._cache_client and dto.job_id:
                await self._update_job_status(dto.job_id, "WA_FAILED", error=str(e))

        return message

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        wa_message_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status in cache."""
        if not self._cache_client:
            return

        import json
        cached_data = await self._cache_client.get(job_id)
        if cached_data:
            try:
                data = json.loads(cached_data)
                data["wa_status"] = status
                if wa_message_id:
                    data["wa_message_id"] = wa_message_id
                if error:
                    data["wa_error"] = error
                await self._cache_client.set(
                    key=job_id,
                    value=json.dumps(data),
                    ttl=self._cache_ttl,
                )
            except json.JSONDecodeError:
                pass
