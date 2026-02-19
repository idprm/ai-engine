"""QuickReply DTOs."""
from datetime import datetime

from pydantic import BaseModel, Field


class QuickReplyDTO(BaseModel):
    """DTO for quick reply data."""

    id: str
    tenant_id: str
    shortcut: str
    content: str
    category: str = "general"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateQuickReplyDTO(BaseModel):
    """DTO for creating a quick reply."""

    shortcut: str = Field(..., min_length=1, max_length=50, description="Shortcut code (must start with /)")
    content: str = Field(..., min_length=1, description="Message content")
    category: str = Field("general", max_length=100, description="Category for organization")

    class Config:
        json_schema_extra = {
            "example": {
                "shortcut": "/hello",
                "content": "Hello! Welcome to our store. How can I help you today?",
                "category": "greeting"
            }
        }


class UpdateQuickReplyDTO(BaseModel):
    """DTO for updating a quick reply."""

    shortcut: str | None = Field(None, min_length=1, max_length=50)
    content: str | None = Field(None, min_length=1)
    category: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class QuickReplyCategoryDTO(BaseModel):
    """DTO for quick reply category with count."""

    name: str
    count: int


class QuickReplyListDTO(BaseModel):
    """DTO for quick reply list with categories."""

    quick_replies: list[QuickReplyDTO]
    categories: list[str]
    total: int
