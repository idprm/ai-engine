"""Message handler for processing WA messages from queue."""
import logging

from waha_sender.application.dto import WAMessageDTO
from waha_sender.application.services import WASenderService

logger = logging.getLogger(__name__)


class WAMessageHandler:
    """Handler for processing WA messages from the queue."""

    def __init__(self, sender_service: WASenderService):
        self._sender_service = sender_service

    async def handle(self, message: dict) -> None:
        """Handle a WA message from the queue.

        Args:
            message: The message payload from the queue.
        """
        # Check if this is a job-to-chat mapping or an actual message to send
        if "job_id" in message and "chat_id" in message and "text" not in message:
            # This is just a mapping, not a message to send
            # The AI engine result will trigger the actual send
            logger.debug(f"Received job mapping: {message.get('job_id')} -> {message.get('chat_id')}")
            return

        # This is an actual message to send
        if "chat_id" not in message or "text" not in message:
            logger.warning(f"Invalid message format, missing chat_id or text: {message}")
            return

        dto = WAMessageDTO.from_dict(message)
        result = await self._sender_service.send_message(dto)

        if result.status.value == "SENT":
            logger.info(f"Message sent successfully to {dto.chat_id}")
        else:
            logger.error(f"Failed to send message to {dto.chat_id}: {result.error}")
