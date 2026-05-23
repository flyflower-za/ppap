import json
from typing import Optional, Any
import redis.asyncio as aioredis
from app.core.config import settings


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Create Redis connection."""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """Set a value in Redis."""
        if not self.redis:
            await self.connect()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.redis:
            await self.connect()
        return await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        if not self.redis:
            await self.connect()
        return await self.redis.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key."""
        if not self.redis:
            await self.connect()
        return await self.redis.expire(key, seconds)


# Global Redis client instance
redis_client = RedisClient()
