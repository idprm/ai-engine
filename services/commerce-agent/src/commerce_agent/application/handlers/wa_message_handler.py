"""WhatsApp message handler for processing incoming messages."""
import logging
from datetime import datetime
from typing import Any

from commerce_agent.application.services.chatbot_orchestrator import ChatbotOrchestrator
from commerce_agent.infrastructure.cache.message_buffer import MessageBuffer
from commerce_agent.infrastructure.location import LocationExtractor

logger = logging.getLogger(__name__)


class WAMessageHandler:
    """Handler for incoming WhatsApp messages from webhook.

    This class provides a simple interface for handling WhatsApp
    webhook messages with message buffering support. When customers
    send multiple messages in quick succession, they are buffered
    and processed together.

    The buffering logic:
    1. First message arrives → start timer (2s delay)
    2. More messages arrive → extend timer (max 10s total)
    3. Timer expires → BufferFlushWorker processes combined message
    """

    def __init__(
        self,
        orchestrator: ChatbotOrchestrator,
        message_buffer: MessageBuffer | None = None,
        location_extractor: LocationExtractor | None = None,
    ):
        """Initialize the handler.

        Args:
            orchestrator: The chatbot orchestrator instance.
            message_buffer: Optional message buffer for batching messages.
            location_extractor: Optional location extractor for processing location data.
        """
        self._orchestrator = orchestrator
        self._buffer = message_buffer
        self._location_extractor = location_extractor

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle a WhatsApp webhook payload.

        This method parses the webhook payload and either:
        - Buffers the message if buffering is enabled, OR
        - Processes immediately if buffering is disabled

        Supports:
        - Text messages
        - Location messages (WhatsApp location sharing)
        - Text messages with Google Maps URLs

        Args:
            payload: The webhook payload from WhatsApp/WAHA.

        Returns:
            Response dict with processing status.
        """
        try:
            # Extract WAHA event data
            event = payload.get("event", "")
            session = payload.get("session", "")
            data = payload.get("data", {})

            # Only handle message events
            if event not in ["message", "message.any"]:
                return {"status": "ignored", "reason": f"Event type: {event}"}

            # Extract message details
            message_data = data.get("body", {})
            from_me = message_data.get("fromMe", False)

            # Ignore messages from the bot itself
            if from_me:
                return {"status": "ignored", "reason": "Own message"}

            # Extract relevant fields
            chat_id = data.get("from", "") or message_data.get("from", "")
            message_id = data.get("id", {}).get("id", "") or message_data.get("id", "")
            message_type = message_data.get("type", "text")

            # Extract phone number from chat_id
            phone_number = None
            if chat_id and "@" in chat_id:
                phone_number = chat_id.split("@")[0]

            # Build base message metadata
            metadata = {
                "message_id": message_id,
                "wa_session": session,
                "chat_id": chat_id,
                "phone_number": phone_number,
                "event": event,
                "timestamp": data.get("timestamp"),
                "type": message_type,
                "tenant_id": payload.get("tenant_id"),
            }

            # Handle location messages
            if message_type == "location":
                location_data = {
                    "latitude": message_data.get("latitude") or data.get("latitude"),
                    "longitude": message_data.get("longitude") or data.get("longitude"),
                    "address": message_data.get("address") or data.get("address"),
                }

                if location_data.get("latitude") is None or location_data.get("longitude") is None:
                    return {"status": "ignored", "reason": "Invalid location data"}

                # Build message with location
                message = {
                    "message_id": message_id,
                    "wa_session": session,
                    "chat_id": chat_id,
                    "phone_number": phone_number,
                    "text": None,  # No text for location messages
                    "location": location_data,
                    "message_type": "location",
                    "metadata": metadata,
                }

                logger.info(f"Received location message from {chat_id}: {location_data}")
                await self._orchestrator.handle_incoming_message(message)

                return {
                    "status": "processed",
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "message_type": "location",
                }

            # Handle text messages
            text = message_data.get("text", "") or data.get("body", "")

            # Skip empty messages
            if not text:
                return {"status": "ignored", "reason": "Empty message"}

            # Check for Google Maps links in text
            location_context = None
            if self._location_extractor:
                location_context = await self._extract_location_from_text(text)

            # If buffering is enabled, add to buffer
            if self._buffer:
                return await self._buffer_message(chat_id, text, metadata, location_context)

            # Otherwise, process immediately
            message = {
                "message_id": message_id,
                "wa_session": session,
                "chat_id": chat_id,
                "phone_number": phone_number,
                "text": text,
                "location": location_context,
                "message_type": "text",
                "metadata": metadata,
            }
            await self._orchestrator.handle_incoming_message(message)

            return {
                "status": "processed",
                "message_id": message_id,
                "chat_id": chat_id,
                "has_location": location_context is not None,
            }

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def _buffer_message(
        self,
        chat_id: str,
        text: str,
        metadata: dict[str, Any],
        location_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a message to the buffer.

        Args:
            chat_id: The WhatsApp chat ID.
            text: The message text.
            metadata: Message metadata.
            location_context: Optional location data extracted from text.

        Returns:
            Response dict with buffering status.
        """
        # Add location context to metadata
        if location_context:
            metadata["location_context"] = location_context

        # Add to buffer
        result = await self._buffer.add_message(
            chat_id=chat_id,
            message=text,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )

        logger.info(
            f"Buffered message {result.message_count} for {chat_id}, "
            f"flush in {result.seconds_until_flush:.1f}s"
        )

        return {
            "status": "buffered",
            "chat_id": chat_id,
            "message_count": result.message_count,
            "seconds_until_flush": result.seconds_until_flush,
            "has_location": location_context is not None,
        }

    async def handle_message_from_queue(self, message_data: dict[str, Any]) -> None:
        """Handle a message from the RabbitMQ queue.

        This is called by the CRM task consumer for each message.

        Args:
            message_data: The message data from the queue.
        """
        await self._orchestrator.handle_incoming_message(message_data)

    async def _extract_location_from_text(self, text: str) -> dict[str, Any] | None:
        """Extract location data from text containing Google Maps URLs.

        Args:
            text: Text that may contain a Google Maps URL.

        Returns:
            Location data dict or None if no location found.
        """
        if not self._location_extractor:
            return None

        try:
            return await self._location_extractor.extract_address_from_message(
                text=text,
                location_data=None,
            )
        except Exception as e:
            logger.error(f"Error extracting location from text: {e}")
            return None

    async def handle_buffered_message(
        self,
        chat_id: str,
        combined_message: str,
        metadata: dict[str, Any],
    ) -> None:
        """Handle a buffered message after flushing.

        This is called by the BufferFlushWorker when a buffer is ready.

        Args:
            chat_id: The WhatsApp chat ID.
            combined_message: Combined text from multiple messages.
            metadata: Metadata from the original messages.
        """
        # Extract location context from metadata if present
        location_context = metadata.pop("location_context", None)

        # Build message for orchestrator
        message = {
            "message_id": metadata.get("message_id", ""),
            "wa_session": metadata.get("wa_session", ""),
            "chat_id": chat_id,
            "phone_number": metadata.get("phone_number"),
            "text": combined_message,
            "location": location_context,
            "message_type": "text",
            "metadata": {
                **metadata,
                "buffered": True,
            },
        }

        await self._orchestrator.handle_incoming_message(message)
