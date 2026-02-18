"""Data Transfer Objects for AI processing operations."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcessingRequest:
    """DTO for a processing request from the message queue."""
    job_id: str
    prompt: str
    config_name: str = "default-smart"
    template_name: str = "default-assistant"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingRequest":
        return cls(
            job_id=data.get("job_id", ""),
            prompt=data.get("prompt", ""),
            config_name=data.get("config_name", "default-smart"),
            template_name=data.get("template_name", "default-assistant"),
        )


@dataclass
class ProcessingResult:
    """DTO for processing result."""
    job_id: str
    status: str
    result: str | None = None
    error: str | None = None
    tokens_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = {
            "job_id": self.job_id,
            "status": self.status,
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        if self.tokens_used > 0:
            data["tokens_used"] = self.tokens_used
        return data
