"""Data Transfer Objects for Job operations."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class JobDTO:
    """DTO for creating a new job."""
    prompt: str
    config_name: str = "default-smart"
    template_name: str = "default-assistant"

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "config_name": self.config_name,
            "template_name": self.template_name,
        }


@dataclass
class JobStatusDTO:
    """DTO for job status response."""
    job_id: str
    status: str
    result: str | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobStatusDTO":
        return cls(
            job_id=data.get("id", data.get("job_id", "")),
            status=data.get("status", "UNKNOWN"),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "job_id": self.job_id,
            "status": self.status,
        }
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
        if self.created_at is not None:
            result["created_at"] = self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        if self.updated_at is not None:
            result["updated_at"] = self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        return result
