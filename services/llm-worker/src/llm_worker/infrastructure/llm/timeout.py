"""Timeout utilities for LLM calls.

This module provides timeout wrappers for LLM API calls to prevent
indefinite hangs when the LLM service is unresponsive.
"""
import asyncio
import logging
from typing import Awaitable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LLMTimeoutError(Exception):
    """Exception raised when an LLM call times out.

    Attributes:
        timeout_seconds: The timeout duration that was exceeded.
        operation: Description of the operation that timed out.
    """

    def __init__(self, timeout_seconds: float, operation: str = "LLM call"):
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout_seconds}s")

    def __str__(self) -> str:
        return f"{self.operation} timed out after {self.timeout_seconds}s"


async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    operation: str = "LLM call",
) -> T:
    """Wrap an awaitable with a timeout.

    Uses asyncio.wait_for to enforce a maximum duration for the operation.
    If the timeout is exceeded, raises LLMTimeoutError.

    Args:
        coro: The coroutine to execute.
        timeout_seconds: Maximum time to wait in seconds.
        operation: Description of the operation for error messages and logging.

    Returns:
        The result of the coroutine.

    Raises:
        LLMTimeoutError: If the operation times out.

    Example:
        ```python
        try:
            response = await with_timeout(
                llm.ainvoke(messages),
                timeout_seconds=120,
                operation="main_agent LLM call",
            )
        except LLMTimeoutError as e:
            logger.error(f"LLM call timed out: {e}")
            # Handle timeout (retry, fallback, etc.)
        ```
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"{operation} timed out after {timeout_seconds}s")
        raise LLMTimeoutError(timeout_seconds, operation)


async def with_timeout_and_fallback(
    coro: Awaitable[T],
    timeout_seconds: float,
    fallback: T | None = None,
    operation: str = "LLM call",
) -> T | None:
    """Wrap an awaitable with timeout and return fallback on timeout.

    Similar to with_timeout, but instead of raising an exception,
    returns the fallback value if the operation times out.

    Args:
        coro: The coroutine to execute.
        timeout_seconds: Maximum time to wait in seconds.
        fallback: Value to return if the operation times out.
        operation: Description of the operation for logging.

    Returns:
        The result of the coroutine, or fallback if timed out.

    Example:
        ```python
        response = await with_timeout_and_fallback(
            llm.ainvoke(messages),
            timeout_seconds=60,
            fallback=AIMessage(content="Request timed out"),
            operation="quick_llm_call",
        )
        ```
    """
    try:
        return await with_timeout(coro, timeout_seconds, operation)
    except LLMTimeoutError:
        logger.info(f"{operation} timed out, returning fallback")
        return fallback
