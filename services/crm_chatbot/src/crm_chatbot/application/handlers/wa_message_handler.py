"""WhatsApp message handler for processing incoming messages."""
import logging
from typing import Any

from crm_chatbot.application.services.chatbot_orchestrator import ChatbotOrchestrator

logger = logging.getLogger(__name__)


class WAMessageHandler:
    """Handler for incoming WhatsApp messages from webhook.

    This class provides a simple interface for handling WhatsApp
    webhook messages and routing them to the chatbot orchestrator.
    """

    def __init__(self, orchestrator: ChatbotOrchestrator):
        """Initialize the handler.

        Args:
            orchestrator: The chatbot orchestrator instance.
        """
        self._orchestrator = orchestrator

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle a WhatsApp webhook payload.

        This method parses the webhook payload and processes each message.

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

            # Build message for processing
            message = {
                "message_id": message_id,
                "wa_session": session,
                "chat_id": chat_id,
                "phone_number": phone_number,
                "text": text,
                "metadata": {
                    "event": event,
                    "timestamp": data.get("timestamp"),
                    "type": message_data.get("type", "text"),
                },
            }

            # Process through orchestrator
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

    async def handle_message_from_queue(self, message_data: dict[str, Any]) -> None:
        """Handle a message from the RabbitMQ queue.

        Args:
            message_data: The message data from the queue.
        """
        await self._orchestrator.handle_incoming_message(message_data)
