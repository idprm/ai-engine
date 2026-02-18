"""Application service for WhatsApp operations."""
import json
import logging
from typing import Protocol

from gateway.application.dto import WAMessageDTO, WAOutgoingMessageDTO, JobDTO
from gateway.application.services.job_service import JobService
from gateway.domain.entities import WAMessage
from gateway.domain.value_objects import WAChatId, WAMessageId, WAEventType, WAEventKind
from shared.exceptions import ValidationException

logger = logging.getLogger(__name__)


class WAMessagePublisher(Protocol):
    """Protocol for publishing WA messages to queue."""

    async def publish_wa_message(self, message: dict) -> None:
        """Publish a WA message to the outgoing queue."""
        ...


class WAService:
    """Application service for WhatsApp webhook operations.

    Handles incoming webhook events from WAHA and creates jobs for processing.
    """

    def __init__(
        self,
        job_service: JobService,
        wa_publisher: WAMessagePublisher,
        default_config_name: str = "default-smart",
        default_template_name: str = "default-assistant",
    ):
        self._job_service = job_service
        self._wa_publisher = wa_publisher
        self._default_config_name = default_config_name
        self._default_template_name = default_template_name

    async def handle_webhook_event(self, dto: WAMessageDTO) -> None:
        """Process incoming WAHA webhook event.

        Args:
            dto: Webhook event data.

        Raises:
            ValidationException: If the event data is invalid.
        """
        event_type = dto.event_type
        logger.info(f"Received WA webhook event: {event_type} from session {dto.session}")

        # Handle different event types
        if event_type in ("message", "message.any"):
            await self._handle_message_event(dto)
        elif event_type == "message.reaction":
            await self._handle_reaction_event(dto)
        elif event_type == "session.status":
            await self._handle_session_status_event(dto)
        else:
            logger.debug(f"Ignoring event type: {event_type}")

    async def _handle_message_event(self, dto: WAMessageDTO) -> None:
        """Handle incoming message event."""
        # Skip messages from me (sent by us)
        if dto.from_me:
            logger.debug(f"Skipping message from me: {dto.message_id}")
            return

        # Skip if no text content
        if not dto.text:
            logger.debug(f"Skipping message with no text: {dto.message_id}")
            return

        try:
            # Create domain objects
            message_id = WAMessageId.from_string(dto.message_id or dto.event_id)
            chat_id = WAChatId(dto.chat_id) if dto.chat_id else None

            if not chat_id:
                logger.warning(f"No chat_id in message: {dto.message_id}")
                return

            event_type = WAEventType(WAEventKind.MESSAGE)

            # Create domain entity
            wa_message = WAMessage.from_webhook(
                message_id=message_id,
                chat_id=chat_id,
                event_type=event_type,
                session=dto.session,
                from_me=dto.from_me,
                text=dto.text or "",
                timestamp=dto.timestamp,
                raw_payload=dto.raw_payload,
            )

            # Create an AI processing job for this message
            job_dto = JobDTO(
                prompt=dto.text,
                config_name=self._default_config_name,
                template_name=self._default_template_name,
            )
            job_status = await self._job_service.submit_job(job_dto)

            logger.info(
                f"Created job {job_status.job_id} for WA message {message_id} "
                f"from chat {chat_id}"
            )

            # Store mapping of job_id -> chat_id for response routing
            # This will be used by waha-sender to know where to send the response
            await self._store_job_mapping(
                job_id=job_status.job_id,
                chat_id=str(chat_id),
                session=dto.session,
                source_message_id=str(message_id),
            )

        except ValueError as e:
            logger.error(f"Invalid message data: {e}")
            raise ValidationException(str(e), field="message")

    async def _handle_reaction_event(self, dto: WAMessageDTO) -> None:
        """Handle message reaction event."""
        # For now, just log reactions
        logger.info(f"Reaction received: {dto.raw_payload}")

    async def _handle_session_status_event(self, dto: WAMessageDTO) -> None:
        """Handle session status change event."""
        status = dto.raw_payload.get("payload", {}).get("status", "unknown")
        logger.info(f"Session {dto.session} status: {status}")

    async def _store_job_mapping(
        self,
        job_id: str,
        chat_id: str,
        session: str,
        source_message_id: str,
    ) -> None:
        """Store job to chat mapping for response routing.

        This uses the job service's cache to store the mapping.
        The waha-sender service will read this to know where to send responses.
        """
        mapping = {
            "job_id": job_id,
            "chat_id": chat_id,
            "session": session,
            "source_message_id": source_message_id,
        }
        # Publish to WA queue for waha-sender to consume
        await self._wa_publisher.publish_wa_message(mapping)

    async def send_message(self, dto: WAOutgoingMessageDTO) -> None:
        """Queue an outgoing message for sending.

        This publishes the message to the WA queue for waha-sender to process.
        """
        await self._wa_publisher.publish_wa_message(dto.to_dict())
        logger.info(f"Queued WA message to {dto.chat_id}")
