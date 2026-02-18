"""Pydantic schemas for WhatsApp webhook API endpoints."""
from typing import Any

from pydantic import BaseModel, Field


class WAWebhookPayload(BaseModel):
    """WAHA webhook payload schema.

    This matches the WAHA webhook event structure.
    See: https://waha.devlike.pro/docs/how-to/events
    """
    id: str = Field(..., description="Unique event ID", alias="id")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    event: str = Field(..., description="Event type (message, message.any, etc.)")
    session: str = Field(..., description="WhatsApp session name")
    me: dict[str, Any] | None = Field(default=None, description="Current user info")
    payload: dict[str, Any] | None = Field(default=None, description="Event payload")
    metadata: dict[str, Any] | None = Field(default=None, description="Custom metadata")
    environment: dict[str, Any] | None = Field(default=None, description="WAHA environment info")
    engine: str | None = Field(default=None, description="WAHA engine (WEBJS, NOWEB, etc.)")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "evt_1111111111111111111111111111",
                    "timestamp": 1741249702485,
                    "event": "message",
                    "session": "default",
                    "me": {"id": "71111111111@c.us", "pushName": "~"},
                    "payload": {
                        "id": {"fromMe": False, "id": "xxx", "remote": "71111111111@c.us"},
                        "body": "Hello!",
                        "fromMe": False,
                        "from": "71111111111@c.us",
                    },
                }
            ]
        }
    }


class WAWebhookResponse(BaseModel):
    """Response schema for webhook acknowledgment."""
    status: str = Field(default="ok", description="Webhook processing status")
    event_id: str | None = Field(default=None, description="Processed event ID")


class WASendMessageRequest(BaseModel):
    """Request schema for sending a WhatsApp message."""
    chat_id: str = Field(..., description="Chat ID (phone number or group ID)")
    text: str = Field(..., min_length=1, description="Message text")
    session: str = Field(default="default", description="WhatsApp session name")
    reply_to: str | None = Field(default=None, description="Message ID to reply to")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chat_id": "1234567890@c.us",
                    "text": "Hello from AI!",
                    "session": "default",
                }
            ]
        }
    }


class WASendMessageResponse(BaseModel):
    """Response schema for message sending."""
    status: str = Field(default="queued", description="Message status")
    message: str = Field(..., description="Status message")
