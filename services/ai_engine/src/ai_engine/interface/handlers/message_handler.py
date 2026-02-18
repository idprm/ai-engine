"""Message handler for processing RabbitMQ task messages."""
import logging
from typing import Any

from ai_engine.application.dto import ProcessingRequest
from ai_engine.application.services import ProcessingService

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handler for processing incoming task messages.

    Bridges the messaging infrastructure to the application service.
    """

    def __init__(self, processing_service: ProcessingService):
        self._processing_service = processing_service

    async def handle(self, message: dict[str, Any]) -> None:
        """Handle an incoming task message.

        Args:
            message: The parsed message body from RabbitMQ.
        """
        job_id = message.get("job_id", "unknown")
        logger.info(f"Handling message for job: {job_id}")

        # Create processing request
        request = ProcessingRequest.from_dict(message)

        # Process the job
        result = await self._processing_service.process(request)

        logger.info(f"Job {job_id} finished with status: {result.status}")
