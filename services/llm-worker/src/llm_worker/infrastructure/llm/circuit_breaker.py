"""Circuit breaker pattern implementation for LLM calls.

This module provides a circuit breaker to protect against cascading failures
when the LLM service is experiencing issues. The circuit breaker has three
states: CLOSED (normal), OPEN (failing fast), and HALF_OPEN (testing recovery).
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Possible states of a circuit breaker.

    - CLOSED: Normal operation, requests pass through. Failures are counted.
    - OPEN: Failing fast, requests are rejected immediately. After timeout,
            transitions to HALF_OPEN to test if service recovered.
    - HALF_OPEN: Testing recovery. Limited requests are allowed. Success closes
                 the circuit, failure reopens it.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit.
        success_threshold: Number of successes in half-open state to close circuit.
        timeout_seconds: Time in seconds before attempting half-open after opening.
        excluded_exceptions: Exception types that should not count as failures.
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    excluded_exceptions: tuple[Type[Exception], ...] = ()


@dataclass
class CircuitStats:
    """Statistics tracked for circuit breaker."""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_failure_error: str | None = None
    last_state_change: float = field(default_factory=time.time)
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_circuit_opens: int = 0


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests.

    Attributes:
        circuit_name: Name of the circuit breaker.
        failure_count: Number of failures that caused the circuit to open.
        last_error: Description of the last failure.
    """

    def __init__(
        self,
        circuit_name: str,
        failure_count: int,
        last_error: str | None = None,
    ):
        self.circuit_name = circuit_name
        self.failure_count = failure_count
        self.last_error = last_error
        msg = f"Circuit breaker '{circuit_name}' is open after {failure_count} failures"
        if last_error:
            msg += f" (last error: {last_error})"
        super().__init__(msg)

    def __str__(self) -> str:
        return self.args[0] if self.args else super().__str__()


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    The circuit breaker pattern prevents an application from repeatedly
    trying to execute an operation that's likely to fail, allowing it
    to continue without waiting for the fault to be fixed.

    State transitions:
    - CLOSED → OPEN: When failure_count >= failure_threshold
    - OPEN → HALF_OPEN: After timeout_seconds has elapsed
    - HALF_OPEN → CLOSED: When success_count >= success_threshold
    - HALF_OPEN → OPEN: On any failure

    Example:
        ```python
        circuit = CircuitBreaker("llm-openai", CircuitBreakerConfig(
            failure_threshold=5,
            timeout_seconds=60,
        ))

        try:
            result = await circuit.call(llm.ainvoke(messages))
        except CircuitOpenError:
            # Circuit is open, use fallback
            result = await fallback_llm.ainvoke(messages)
        ```
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Circuit breaker name."""
        return self._name

    @property
    def state(self) -> CircuitState:
        """Current circuit breaker state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    @property
    def stats(self) -> CircuitStats:
        """Get current statistics."""
        return self._stats

    async def call(self, coro: Awaitable[T]) -> T:
        """Execute a coroutine through the circuit breaker.

        If the circuit is open and the timeout hasn't elapsed, raises
        CircuitOpenError immediately without attempting the operation.

        Args:
            coro: The coroutine to execute.

        Returns:
            The result of the coroutine.

        Raises:
            CircuitOpenError: If the circuit is open.
            Any exception raised by the coroutine.
        """
        async with self._lock:
            await self._update_state()

            if self._state == CircuitState.OPEN:
                raise CircuitOpenError(
                    circuit_name=self._name,
                    failure_count=self._stats.failure_count,
                    last_error=self._stats.last_failure_error,
                )

            self._stats.total_requests += 1

        # Execute outside the lock to allow concurrent requests in closed state
        try:
            result = await coro
            await self._record_success()
            return result
        except Exception as e:
            # Check if this exception should count as a failure
            if not isinstance(e, self._config.excluded_exceptions):
                await self._record_failure(str(e))
            raise

    async def _update_state(self) -> None:
        """Update circuit state based on time and stats.

        Called with lock held.
        """
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._stats.last_failure_time
            if elapsed >= self._config.timeout_seconds:
                await self._transition_to(CircuitState.HALF_OPEN)

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._stats.success_count += 1
            self._stats.total_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.success_count >= self._config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

            # Reset failure count on success in closed state
            if self._state == CircuitState.CLOSED:
                self._stats.failure_count = 0

    async def _record_failure(self, error_msg: str | None = None) -> None:
        """Record a failed call.

        Args:
            error_msg: Optional error message from the failure.
        """
        async with self._lock:
            self._stats.failure_count += 1
            self._stats.last_failure_time = time.time()
            self._stats.last_failure_error = error_msg
            self._stats.total_failures += 1
            self._stats.success_count = 0  # Reset success count

            if self._state == CircuitState.CLOSED:
                if self._stats.failure_count >= self._config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open returns to open
                await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state.

        Called with lock held.
        """
        old_state = self._state
        self._state = new_state
        self._stats.last_state_change = time.time()

        # Reset counters on state change
        if new_state == CircuitState.CLOSED:
            self._stats.failure_count = 0
            self._stats.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._stats.success_count = 0

        # Track circuit opens
        if new_state == CircuitState.OPEN:
            self._stats.total_circuit_opens += 1

        logger.warning(
            f"Circuit breaker '{self._name}' transitioned: "
            f"{old_state.value} -> {new_state.value}"
        )

    def get_status(self) -> dict[str, Any]:
        """Get current status for monitoring/health checks.

        Returns:
            Dictionary with circuit breaker status information.
        """
        return {
            "name": self._name,
            "state": self._state.value,
            "failure_count": self._stats.failure_count,
            "success_count": self._stats.success_count,
            "total_requests": self._stats.total_requests,
            "total_failures": self._stats.total_failures,
            "total_successes": self._stats.total_successes,
            "total_circuit_opens": self._stats.total_circuit_opens,
            "last_failure_time": self._stats.last_failure_time,
            "last_failure_error": self._stats.last_failure_error,
        }


class CircuitBreakerRegistry:
    """Global registry for circuit breakers.

    Provides a singleton registry to manage circuit breakers by name,
    allowing sharing of circuit breakers across the application for
    the same LLM configurations.

    Example:
        ```python
        registry = CircuitBreakerRegistry.get_instance()
        circuit = registry.get_or_create("llm-gpt4", CircuitBreakerConfig(
            failure_threshold=5,
        ))

        # Get all stats for monitoring
        all_stats = registry.get_all_stats()
        ```
    """

    _instance: "CircuitBreakerRegistry | None" = None
    _circuit_breakers: dict[str, CircuitBreaker]

    def __init__(self) -> None:
        self._circuit_breakers = {}

    @classmethod
    def get_instance(cls) -> "CircuitBreakerRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name.

        If a circuit breaker with the given name exists, returns it.
        Otherwise, creates a new one with the provided config.

        Args:
            name: Unique name for the circuit breaker.
            config: Configuration for new circuit breakers.

        Returns:
            The circuit breaker instance.
        """
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name, config)
        return self._circuit_breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get a circuit breaker by name without creating.

        Args:
            name: The circuit breaker name.

        Returns:
            The circuit breaker or None if not found.
        """
        return self._circuit_breakers.get(name)

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all circuit breakers.

        Returns:
            Dictionary mapping circuit breaker names to their stats.
        """
        return {
            name: circuit.get_status()
            for name, circuit in self._circuit_breakers.items()
        }

    def get_all_states(self) -> dict[str, str]:
        """Get states for all circuit breakers.

        Returns:
            Dictionary mapping circuit breaker names to their state.
        """
        return {
            name: circuit.state.value
            for name, circuit in self._circuit_breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers (useful for testing)."""
        self._circuit_breakers.clear()
