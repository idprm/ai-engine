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
        return data
