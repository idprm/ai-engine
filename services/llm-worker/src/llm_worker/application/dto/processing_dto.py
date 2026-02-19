"""Data Transfer Objects for AI processing operations."""
from dataclasses import dataclass
from typing import Any


@dataclass
class ProcessingRequest:
    """DTO for a processing request from the message queue."""

    job_id: str
    prompt: str
    config_name: str = "default-smart"
    template_name: str = "default-assistant"
    agent_type: str | None = None
    context: dict[str, Any] | None = None
    use_multi_agent: bool = False
    needs_moderation: bool = True
    retry_count: int = 0  # Current retry attempt (0 = first attempt)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingRequest":
        return cls(
            job_id=data.get("job_id", ""),
            prompt=data.get("prompt", ""),
            config_name=data.get("config_name", "default-smart"),
            template_name=data.get("template_name", "default-assistant"),
            agent_type=data.get("agent_type"),
            context=data.get("context"),
            use_multi_agent=data.get("use_multi_agent", False),
            needs_moderation=data.get("needs_moderation", True),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class ProcessingResult:
    """DTO for processing result."""

    job_id: str
    status: str
    result: str | None = None
    error: str | None = None
    tokens_used: int = 0
    agent_type: str | None = None
    retry_count: int = 0  # Current retry count
    should_retry: bool = False  # Whether job should be retried
    retry_delay_seconds: float | None = None  # Delay before retry

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status,
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        if self.tokens_used > 0:
            data["tokens_used"] = self.tokens_used
        if self.agent_type is not None:
            data["agent_type"] = self.agent_type
        if self.retry_count > 0:
            data["retry_count"] = self.retry_count
        if self.should_retry:
            data["should_retry"] = self.should_retry
        if self.retry_delay_seconds is not None:
            data["retry_delay_seconds"] = self.retry_delay_seconds
        return data

    @classmethod
    def success(
        cls,
        job_id: str,
        result: str,
        tokens_used: int = 0,
        agent_type: str | None = None,
    ) -> "ProcessingResult":
        """Create a successful result."""
        return cls(
            job_id=job_id,
            status="COMPLETED",
            result=result,
            tokens_used=tokens_used,
            agent_type=agent_type,
        )

    @classmethod
    def failure(
        cls,
        job_id: str,
        error: str,
        retry_count: int = 0,
        should_retry: bool = False,
        retry_delay_seconds: float | None = None,
    ) -> "ProcessingResult":
        """Create a failed result."""
        return cls(
            job_id=job_id,
            status="FAILED",
            error=error,
            retry_count=retry_count,
            should_retry=should_retry,
            retry_delay_seconds=retry_delay_seconds,
        )

    @classmethod
    def retryable_failure(
        cls,
        job_id: str,
        error: str,
        retry_count: int,
        max_retries: int = 3,
        base_delay: float = 5.0,
    ) -> "ProcessingResult":
        """Create a retryable failure result with backoff."""
        if retry_count >= max_retries:
            # No more retries
            return cls(
                job_id=job_id,
                status="FAILED",
                error=f"{error} (max retries exceeded)",
                retry_count=retry_count,
                should_retry=False,
            )

        # Calculate exponential backoff delay
        delay = min(base_delay * (2**retry_count), 300.0)  # Max 5 minutes

        return cls(
            job_id=job_id,
            status="FAILED",
            error=error,
            retry_count=retry_count,
            should_retry=True,
            retry_delay_seconds=delay,
        )
