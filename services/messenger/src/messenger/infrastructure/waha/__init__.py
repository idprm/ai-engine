"""WAHA API client implementation."""
import logging
from typing import Any

import httpx

from shared.config import get_settings

logger = logging.getLogger(__name__)


class WAHAClient:
    """Client for WAHA (WhatsApp HTTP API).

    Documentation: https://waha.devlike.pro/docs/
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_session: str | None = None,
    ):
        settings = get_settings()
        self._base_url = (base_url or settings.waha_server_url).rstrip("/")
        self._api_key = api_key or settings.waha_api_key
        self._default_session = default_session or settings.waha_session
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        return headers

    async def send_text(
        self,
        chat_id: str,
        text: str,
        session: str | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Send a text message.

        Args:
            chat_id: Chat ID (phone number or group ID).
            text: Message text.
            session: Session name (defaults to configured session).
            reply_to: Message ID to reply to.

        Returns:
            WAHA response with message ID.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        session = session or self._default_session
        url = f"{self._base_url}/api/sendText"

        payload = {
            "chatId": chat_id,
            "text": text,
            "session": session,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        logger.debug(f"Sending text to {chat_id}: {text[:50]}...")

        response = await self._client.post(
            url,
            json=payload,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        result = response.json()
        logger.info(f"Message sent to {chat_id}: {result.get('id', 'unknown')}")

        return result

    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: str | None = None,
        session: str | None = None,
    ) -> dict[str, Any]:
        """Send an image message.

        Args:
            chat_id: Chat ID.
            image_url: URL of the image.
            caption: Optional caption.
            session: Session name.

        Returns:
            WAHA response.
        """
        session = session or self._default_session
        url = f"{self._base_url}/api/sendImage"

        payload = {
            "chatId": chat_id,
            "file": {"url": image_url},
            "session": session,
        }
        if caption:
            payload["caption"] = caption

        response = await self._client.post(
            url,
            json=payload,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        return response.json()

    async def get_session_status(self, session: str | None = None) -> dict[str, Any]:
        """Get session status.

        Args:
            session: Session name.

        Returns:
            Session status information.
        """
        session = session or self._default_session
        url = f"{self._base_url}/api/sessions/{session}"

        response = await self._client.get(
            url,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        return response.json()

    async def check_health(self) -> bool:
        """Check if WAHA server is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            url = f"{self._base_url}/api/sessions"
            response = await self._client.get(
                url,
                headers=self._get_headers(),
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"WAHA health check failed: {e}")
            return False
