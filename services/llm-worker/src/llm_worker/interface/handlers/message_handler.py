"""Message handler for processing RabbitMQ task messages."""
import logging
from typing import Any, Callable, Coroutine

from llm_worker.application.dto import ProcessingRequest, ProcessingResult
from llm_worker.application.services import ProcessingService

logger = logging.getLogger(__name__)


# Type for retry scheduler callback
RetryScheduler = Callable[[str, dict[str, Any], float], Coroutine[Any, Any, None]]


class MessageHandler:
    """Handler for processing incoming task messages.

    Bridges the messaging infrastructure to the application service.
    Supports retry scheduling for transient failures.
    """

    def __init__(
        self,
        processing_service: ProcessingService,
        retry_scheduler: RetryScheduler | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 5.0,
    ):
        """Initialize the message handler.

        Args:
            processing_service: Service for processing jobs.
            retry_scheduler: Optional async callback for scheduling retries.
                Signature: (job_id, message, delay_seconds) -> None
            max_retries: Maximum number of retry attempts.
            retry_base_delay: Base delay in seconds for exponential backoff.
        """
        self._processing_service = processing_service
        self._retry_scheduler = retry_scheduler
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    async def handle(self, message: dict[str, Any]) -> ProcessingResult:
        """Handle an incoming task message.

        Args:
            message: The parsed message body from RabbitMQ.

        Returns:
            The processing result.
        """
        job_id = message.get("job_id", "unknown")
        retry_count = message.get("retry_count", 0)

        logger.info(f"Handling message for job: {job_id}, retry: {retry_count}")

        # Create processing request
        request = ProcessingRequest.from_dict(message)

        # Process the job
        result = await self._processing_service.process(request)

        # Handle retry logic
        if result.status == "FAILED" and result.should_retry:
            await self._schedule_retry(job_id, message, result)
        elif result.status == "FAILED":
            # Check if we should retry despite the result saying no
            if retry_count < self._max_retries and self._is_retryable_error(result.error):
                await self._schedule_retry(job_id, message, result, force_retry=True)

        logger.info(f"Job {job_id} finished with status: {result.status}")
        return result

    async def _schedule_retry(
        self,
        job_id: str,
        message: dict[str, Any],
        result: ProcessingResult,
        force_retry: bool = False,
    ) -> None:
        """Schedule a retry for a failed job.

        Args:
            job_id: The job identifier.
            message: The original message.
            result: The processing result.
            force_retry: Force a retry even if result says no.
        """
        retry_count = message.get("retry_count", 0)

        if retry_count >= self._max_retries:
            logger.warning(
                f"Job {job_id} has exceeded max retries ({self._max_retries}), "
                "not scheduling retry"
            )
            return

        if not self._retry_scheduler:
            logger.warning(
                f"No retry scheduler configured, cannot retry job {job_id}"
            )
            return

        # Calculate delay
        delay = result.retry_delay_seconds
        if delay is None:
            # Use exponential backoff
            delay = min(
                self._retry_base_delay * (2**retry_count),
                300.0,  # Max 5 minutes
            )

        # Update message for retry
        retry_message = {
            **message,
            "retry_count": retry_count + 1,
            "previous_error": result.error,
        }

        logger.info(
            f"Scheduling retry for job {job_id} in {delay:.2f}s "
            f"(attempt {retry_count + 1}/{self._max_retries})"
        )

        await self._retry_scheduler(job_id, retry_message, delay)

    def _is_retryable_error(self, error: str | None) -> bool:
        """Check if an error is retryable.

        Args:
            error: The error message.

        Returns:
            True if the error might succeed on retry.
        """
        if not error:
            return True

        # Non-retryable error patterns
        non_retryable_patterns = [
            "content policy",
            "policy violation",
            "invalid request",
            "invalid api key",
            "authentication",
            "unauthorized",
            "quota exceeded",
            "rate limit",
        ]

        error_lower = error.lower()
        for pattern in non_retryable_patterns:
            if pattern in error_lower:
                return False

        return True
