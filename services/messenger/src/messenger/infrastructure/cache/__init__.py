"""Redis cache client implementation."""
import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client for storing job status."""

    def __init__(self, url: str):
        self._url = url
        self._client: redis.Redis | None = None

    async def connect(self):
        """Connect to Redis."""
        if self._client:
            return

        self._client = redis.from_url(self._url)
        logger.info("Connected to Redis")

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        if not self._client:
            return None
        value = await self._client.get(key)
        return value.decode() if value else None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        if not self._client:
            return
        await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if not self._client:
            return
        await self._client.delete(key)
