"""Pydantic schemas for job API endpoints."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubmitJobRequest(BaseModel):
    """Request schema for submitting a new job."""
    prompt: str = Field(..., min_length=1, max_length=100000, description="User prompt for AI processing")
    config_name: str = Field(default="default-smart", description="LLM configuration name")
    template_name: str = Field(default="default-assistant", description="Prompt template name")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Write a haiku about programming",
                    "config_name": "default-smart",
                    "template_name": "default-assistant",
                }
            ]
        }
    }


class SubmitJobResponse(BaseModel):
    """Response schema for job submission."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial job status")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "QUEUED",
                }
            ]
        }
    }


class JobStatusResponse(BaseModel):
    """Response schema for job status query."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    result: str | None = Field(default=None, description="Job result (when completed)")
    error: str | None = Field(default=None, description="Error message (when failed)")
    created_at: str | None = Field(default=None, description="Job creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "COMPLETED",
                    "result": "Code flows like water\nBugs hide in the logic streams\nDebug brings clarity",
                    "error": None,
                    "created_at": "2024-01-15T10:30:00",
                    "updated_at": "2024-01-15T10:30:05",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str = Field(..., description="Error message")
    code: str | None = Field(default=None, description="Error code")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Job not found",
                    "code": "NOT_FOUND",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="healthy", description="Service health status")
    service: str = Field(default="gateway", description="Service name")
