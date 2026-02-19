"""WhatsApp message handler for processing incoming messages."""
import logging
from datetime import datetime
from typing import Any

from crm_chatbot.application.services.chatbot_orchestrator import ChatbotOrchestrator
from crm_chatbot.infrastructure.cache.message_buffer import MessageBuffer

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
    ):
        """Initialize the handler.

        Args:
            orchestrator: The chatbot orchestrator instance.
            message_buffer: Optional message buffer for batching messages.
        """
        self._orchestrator = orchestrator
        self._buffer = message_buffer

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle a WhatsApp webhook payload.

        This method parses the webhook payload and either:
        - Buffers the message if buffering is enabled, OR
        - Processes immediately if buffering is disabled

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
            text = message_data.get("text", "") or data.get("body", "")

            # Skip empty messages or non-text messages
            if not text:
                return {"status": "ignored", "reason": "Empty or non-text message"}

            # Extract phone number from chat_id
            phone_number = None
            if chat_id and "@" in chat_id:
                phone_number = chat_id.split("@")[0]

            # Build message metadata
            metadata = {
                "message_id": message_id,
                "wa_session": session,
                "chat_id": chat_id,
                "phone_number": phone_number,
                "event": event,
                "timestamp": data.get("timestamp"),
                "type": message_data.get("type", "text"),
                "tenant_id": payload.get("tenant_id"),
            }

            # If buffering is enabled, add to buffer
            if self._buffer:
                return await self._buffer_message(chat_id, text, metadata)

            # Otherwise, process immediately
            message = {
                "message_id": message_id,
                "wa_session": session,
                "chat_id": chat_id,
                "phone_number": phone_number,
                "text": text,
                "metadata": metadata,
            }
            await self._orchestrator.handle_incoming_message(message)

            return {
                "status": "processed",
                "message_id": message_id,
                "chat_id": chat_id,
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
    ) -> dict[str, Any]:
        """Add a message to the buffer.

        Args:
            chat_id: The WhatsApp chat ID.
            text: The message text.
            metadata: Message metadata.

        Returns:
            Response dict with buffering status.
        """
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
        }

    async def handle_message_from_queue(self, message_data: dict[str, Any]) -> None:
        """Handle a message from the RabbitMQ queue.

        This is called by the CRM task consumer for each message.

        Args:
            message_data: The message data from the queue.
        """
        await self._orchestrator.handle_incoming_message(message_data)

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
        # Build message for orchestrator
        message = {
            "message_id": metadata.get("message_id", ""),
            "wa_session": metadata.get("wa_session", ""),
            "chat_id": chat_id,
            "phone_number": metadata.get("phone_number"),
            "text": combined_message,
            "metadata": {
                **metadata,
                "buffered": True,
            },
        }

        await self._orchestrator.handle_incoming_message(message)
