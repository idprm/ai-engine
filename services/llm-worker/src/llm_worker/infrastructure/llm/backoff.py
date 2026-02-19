"""Exponential backoff utilities for retry logic.

This module provides configurable exponential backoff with jitter for
retry operations, helping to prevent thundering herd problems and
allowing services time to recover.
"""
import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class BackoffConfig:
    """Configuration for exponential backoff.

    Attributes:
        initial_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap in seconds.
        multiplier: Factor to multiply delay by after each attempt.
        jitter_factor: Random jitter factor (0.0 to 1.0) to add variation.
    """

    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter_factor: float = 0.1

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt with jitter.

        Uses exponential backoff with full jitter strategy:
        delay = min(max_delay, initial_delay * multiplier^attempt) + random_jitter

        This prevents thundering herd while maintaining backoff behavior.

        Args:
            attempt: The attempt number (0-indexed).

        Returns:
            The delay in seconds for this attempt.
        """
        # Calculate base exponential delay
        delay = self.initial_delay * (self.multiplier**attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Apply jitter (random variation to prevent synchronized retries)
        if self.jitter_factor > 0:
            jitter = random.uniform(0, delay * self.jitter_factor)
            delay = delay + jitter

        return min(delay, self.max_delay)


class BackoffExhaustedError(Exception):
    """Raised when all retry attempts are exhausted.

    Attributes:
        attempts: Total number of attempts made.
        last_error: The last exception that occurred, if any.
    """

    def __init__(self, attempts: int, last_error: Exception | None = None):
        self.attempts = attempts
        self.last_error = last_error
        msg = f"All {attempts} retry attempts exhausted"
        if last_error:
            msg += f": {last_error}"
        super().__init__(msg)

    def __str__(self) -> str:
        msg = f"All {self.attempts} retry attempts exhausted"
        if self.last_error:
            msg += f" (last error: {self.last_error})"
        return msg


async def retry_with_backoff(
    coro_factory: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    backoff_config: BackoffConfig | None = None,
    retryable_exceptions: tuple[Type[Exception], ...] | None = None,
    operation_name: str = "operation",
) -> T:
    """Execute a coroutine with exponential backoff retry.

    Creates and executes the coroutine from the factory function,
    retrying with exponential backoff if specified exceptions occur.

    Args:
        coro_factory: Factory function that creates the coroutine to retry.
            Should be a callable that returns an awaitable.
        max_retries: Maximum number of retry attempts (not including initial).
        backoff_config: Backoff configuration. Uses defaults if None.
        retryable_exceptions: Tuple of exception types that should trigger retry.
            Defaults to (Exception,) which retries on all exceptions.
        operation_name: Name of the operation for logging.

    Returns:
        The result of the successful coroutine execution.

    Raises:
        BackoffExhaustedError: When all retries are exhausted.
        Any non-retryable exception from the coroutine.

    Example:
        ```python
        async def make_llm_call():
            return await llm.ainvoke(messages)

        try:
            result = await retry_with_backoff(
                coro_factory=make_llm_call,
                max_retries=3,
                backoff_config=BackoffConfig(initial_delay=1.0, max_delay=30.0),
                retryable_exceptions=(LLMTimeoutError, ConnectionError),
                operation_name="LLM call",
            )
        except BackoffExhaustedError:
            # All retries failed
            logger.error("LLM call failed after all retries")
        ```
    """
    if backoff_config is None:
        backoff_config = BackoffConfig()

    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)

    last_error: Exception | None = None
    total_attempts = max_retries + 1  # Initial attempt + retries

    for attempt in range(total_attempts):
        try:
            return await coro_factory()
        except retryable_exceptions as e:
            last_error = e

            if attempt >= max_retries:
                logger.error(
                    f"{operation_name}: All {max_retries} retries exhausted. "
                    f"Last error: {e}"
                )
                raise BackoffExhaustedError(total_attempts, last_error)

            delay = backoff_config.calculate_delay(attempt)
            logger.warning(
                f"{operation_name}: Attempt {attempt + 1}/{total_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

    # Should never reach here, but type checker needs it
    raise BackoffExhaustedError(total_attempts, last_error)


async def retry_with_backoff_and_fallback(
    coro_factory: Callable[[], Awaitable[T]],
    fallback_factory: Callable[[], Awaitable[T]] | Callable[[], T] | T,
    max_retries: int = 3,
    backoff_config: BackoffConfig | None = None,
    retryable_exceptions: tuple[Type[Exception], ...] | None = None,
    operation_name: str = "operation",
) -> T:
    """Execute with retry and return fallback if all retries fail.

    Similar to retry_with_backoff, but instead of raising BackoffExhaustedError,
    returns a fallback value/function result when all retries are exhausted.

    Args:
        coro_factory: Factory function that creates the coroutine to retry.
        fallback_factory: Either:
            - An async callable that returns the fallback value
            - A sync callable that returns the fallback value
            - The fallback value directly
        max_retries: Maximum number of retry attempts.
        backoff_config: Backoff configuration.
        retryable_exceptions: Exceptions that trigger retry.
        operation_name: Name for logging.

    Returns:
        The result of the coroutine, or the fallback value.

    Example:
        ```python
        result = await retry_with_backoff_and_fallback(
            coro_factory=lambda: llm.ainvoke(messages),
            fallback_factory=lambda: AIMessage(content="Service temporarily unavailable"),
            max_retries=2,
        )
        ```
    """
    try:
        return await retry_with_backoff(
            coro_factory=coro_factory,
            max_retries=max_retries,
            backoff_config=backoff_config,
            retryable_exceptions=retryable_exceptions,
            operation_name=operation_name,
        )
    except BackoffExhaustedError:
        logger.info(f"{operation_name}: Returning fallback after all retries failed")

        # Handle different fallback types
        if callable(fallback_factory):
            result = fallback_factory()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return fallback_factory
