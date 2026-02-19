"""Background worker for flushing message buffers.

Periodically checks all active message buffers and flushes them
when ready, publishing the combined messages for processing.
"""
import asyncio
import json
import logging
from typing import Callable, Coroutine

from commerce_agent.infrastructure.cache.message_buffer import MessageBuffer

logger = logging.getLogger(__name__)


# Type for the message processor callback
MessageProcessorCallback = Callable[[str, str, dict], Coroutine[None, None, None]]


class BufferFlushWorker:
    """Background worker that flushes message buffers when ready.

    Runs as a background task that periodically scans for buffers
    ready to flush and publishes them for processing.

    Flow:
    1. Worker scans all active buffers every CHECK_INTERVAL seconds
    2. For each buffer ready to flush, gets combined message
    3. Calls the message processor callback with combined message
    4. Message processor handles AI processing and response

    Usage:
        worker = BufferFlushWorker(message_buffer, processor_callback)
        task = asyncio.create_task(worker.start())
        # ... later ...
        await worker.stop()
    """

    CHECK_INTERVAL = 0.5  # How often to check buffers (seconds)

    def __init__(
        self,
        message_buffer: MessageBuffer,
        message_processor: MessageProcessorCallback,
        check_interval: float = 0.5,
    ):
        """Initialize the buffer flush worker.

        Args:
            message_buffer: The MessageBuffer instance to check.
            message_processor: Async callback to process flushed messages.
                Signature: async def processor(chat_id: str, message: str, metadata: dict)
            check_interval: How often to check buffers (seconds).
        """
        self._buffer = message_buffer
        self._processor = message_processor
        self._check_interval = check_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the flush worker loop.

        This runs continuously until stop() is called.
        """
        if self._running:
            logger.warning("BufferFlushWorker already running")
            return

        self._running = True
        logger.info(
            f"BufferFlushWorker started, checking every {self._check_interval}s"
        )

        while self._running:
            try:
                await self._check_and_flush_buffers()
            except Exception as e:
                logger.error(f"Error in buffer flush loop: {e}", exc_info=True)

            await asyncio.sleep(self._check_interval)

        logger.info("BufferFlushWorker stopped")

    async def stop(self) -> None:
        """Stop the flush worker loop."""
        logger.info("Stopping BufferFlushWorker...")
        self._running = False

        # Flush any remaining buffers before stopping
        try:
            await self._flush_all_remaining()
        except Exception as e:
            logger.error(f"Error flushing remaining buffers: {e}", exc_info=True)

    async def _check_and_flush_buffers(self) -> None:
        """Check all active buffers and flush if ready."""
        try:
            # Get all chat IDs with active buffers
            chat_ids = await self._buffer.get_all_active_chat_ids()

            if not chat_ids:
                return

            logger.debug(f"Checking {len(chat_ids)} active buffers")

            # Check each buffer
            for chat_id in chat_ids:
                try:
                    if await self._buffer.should_flush(chat_id):
                        await self._flush_and_process(chat_id)
                except Exception as e:
                    logger.error(f"Error processing buffer for {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Error scanning buffers: {e}", exc_info=True)

    async def _flush_and_process(self, chat_id: str) -> None:
        """Flush a buffer and process the combined message.

        Args:
            chat_id: The WhatsApp chat ID to flush.
        """
        # Get combined message
        combined = await self._buffer.get_combined_message(chat_id)

        if not combined:
            logger.debug(f"No messages in buffer for {chat_id}")
            return

        logger.info(f"Processing buffered message for {chat_id}: {len(combined)} chars")

        # Build metadata
        metadata = {
            "buffered": True,
            "original_length": len(combined),
        }

        # Call the message processor
        try:
            await self._processor(chat_id, combined, metadata)
        except Exception as e:
            logger.error(f"Message processor failed for {chat_id}: {e}", exc_info=True)

    async def _flush_all_remaining(self) -> None:
        """Flush all remaining buffers on shutdown."""
        chat_ids = await self._buffer.get_all_active_chat_ids()

        if not chat_ids:
            return

        logger.info(f"Flushing {len(chat_ids)} remaining buffers")

        for chat_id in chat_ids:
            try:
                await self._flush_and_process(chat_id)
            except Exception as e:
                logger.error(f"Error flushing {chat_id} on shutdown: {e}")

    def start_as_task(self) -> asyncio.Task:
        """Start the worker as a background task.

        Returns:
            The asyncio.Task running the worker.
        """
        if self._task and not self._task.done():
            logger.warning("BufferFlushWorker task already running")
            return self._task

        self._task = asyncio.create_task(self.start())
        return self._task
