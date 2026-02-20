"""Message DTOs for WhatsApp communication."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WhatsAppMessageDTO(BaseModel):
    """DTO for incoming WhatsApp message."""

    message_id: str = Field(..., description="WhatsApp message ID")
    wa_session: str = Field(..., description="WAHA session name")
    chat_id: str = Field(..., description="WhatsApp chat ID")
    phone_number: str | None = Field(None, description="Sender phone number")
    text: str | None = Field(None, description="Message text content (optional for location messages)")
    timestamp: datetime | None = Field(None, description="Message timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Location fields for WhatsApp location messages
    location: dict[str, Any] | None = Field(
        None,
        description="Location data with latitude, longitude, and optional address"
    )
    message_type: str = Field(
        default="text",
        description="Message type: text, location, image, etc."
    )


class WhatsAppResponseDTO(BaseModel):
    """DTO for outgoing WhatsApp response."""

    message_id: str | None = Field(None, description="Generated message ID")
    wa_session: str = Field(..., description="WAHA session name")
    chat_id: str = Field(..., description="Target WhatsApp chat ID")
    text: str = Field(..., description="Response text")
    reply_to: str | None = Field(None, description="Original message ID to reply to")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class ChatbotResponseDTO(BaseModel):
    """DTO for chatbot processing result."""

    response_text: str = Field(..., description="AI generated response")
    conversation_id: str = Field(..., description="Conversation ID")
    conversation_state: str = Field(..., description="Current conversation state")
    intent: str | None = Field(None, description="Detected intent")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    tools_used: list[str] = Field(default_factory=list, description="Tools invoked")
    needs_human_handoff: bool = Field(default=False, description="Whether to escalate to human")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
