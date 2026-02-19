"""Message DTOs for RabbitMQ messages."""
from dataclasses import dataclass
from typing import Any


@dataclass
class TaskMessage:
    """DTO for task messages from RabbitMQ."""
    job_id: str
    prompt: str
    config_name: str = "default-smart"
    template_name: str = "default-assistant"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskMessage":
        return cls(
            job_id=data.get("job_id", ""),
            prompt=data.get("prompt", ""),
            config_name=data.get("config_name", "default-smart"),
            template_name=data.get("template_name", "default-assistant"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "prompt": self.prompt,
            "config_name": self.config_name,
            "template_name": self.template_name,
        }
