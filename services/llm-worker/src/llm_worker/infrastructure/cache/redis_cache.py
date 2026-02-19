"""Redis cache client implementation for AI Engine."""
import json
import logging
from typing import Any

import redis.asyncio as redis

from shared.config import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client for AI Engine.

    Used for updating job status after processing.
    """

    def __init__(self, url: str | None = None):
        settings = get_settings()
        self._url = url or settings.redis_url
        self._client: redis.Redis | None = None

    async def connect(self):
        """Establish connection to Redis."""
        if self._client:
            return

        self._client = redis.from_url(self._url, decode_responses=True)
        logger.info("Connected to Redis")

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        await self.connect()
        value = await self._client.get(key)
        return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        await self.connect()
        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        await self.connect()
        return bool(await self._client.delete(key))

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        await self.connect()
        return bool(await self._client.exists(key))

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode JSON for key: {key}")
        return None

    async def set_json(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Set JSON value in cache."""
        await self.set(key, json.dumps(value), ttl=ttl)
