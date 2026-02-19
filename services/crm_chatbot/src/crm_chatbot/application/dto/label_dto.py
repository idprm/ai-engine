"""Label DTOs."""
from datetime import datetime

from pydantic import BaseModel, Field


class LabelDTO(BaseModel):
    """DTO for label data."""

    id: str
    tenant_id: str
    name: str
    color: str = "#3498db"
    description: str = ""
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateLabelDTO(BaseModel):
    """DTO for creating a label."""

    name: str = Field(..., min_length=1, max_length=100, description="Label name")
    color: str = Field("#3498db", pattern=r'^#[0-9A-Fa-f]{6}$', description="Hex color code")
    description: str = Field("", max_length=500, description="Label description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Follow Up",
                "color": "#e74c3c",
                "description": "Conversations that need follow-up"
            }
        }


class UpdateLabelDTO(BaseModel):
    """DTO for updating a label."""

    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class ApplyLabelDTO(BaseModel):
    """DTO for applying a label to a conversation."""

    label_id: str = Field(..., description="Label ID to apply")
    applied_by: str | None = Field(None, description="Who applied the label (ai, human, or user_id)")


class BatchApplyLabelsDTO(BaseModel):
    """DTO for batch applying labels to conversations."""

    conversation_ids: list[str] = Field(..., min_length=1, description="List of conversation IDs")
    label_ids: list[str] = Field(..., min_length=1, description="List of label IDs to apply")
    applied_by: str | None = Field(None, description="Who applied the labels")


class ConversationLabelsDTO(BaseModel):
    """DTO for conversation with its labels."""

    conversation_id: str
    labels: list[LabelDTO]


class LabelWithConversationsDTO(BaseModel):
    """DTO for label with conversation count."""

    id: str
    tenant_id: str
    name: str
    color: str
    description: str
    is_active: bool
    conversation_count: int = 0
    created_at: datetime
    updated_at: datetime
