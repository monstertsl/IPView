import json
from datetime import timedelta
from typing import Optional
import redis.asyncio as redis

from app.core.config import settings

redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


class RedisSession:
    """Redis session/token cache."""

    @staticmethod
    async def set(key: str, value: dict, expire: int = 1800):
        r = await get_redis()
        await r.setex(key, expire, json.dumps(value, default=str))

    @staticmethod
    async def get(key: str) -> Optional[dict]:
        r = await get_redis()
        data = await r.get(key)
        if data:
            return json.loads(data)
        return None

    @staticmethod
    async def delete(key: str):
        r = await get_redis()
        await r.delete(key)

    @staticmethod
    async def set_ip_status(ip: str, status: str, expire: int = 300):
        r = await get_redis()
        await r.setex(f"ip:status:{ip}", expire, status)

    @staticmethod
    async def get_ip_status(ip: str) -> Optional[str]:
        r = await get_redis()
        return await r.get(f"ip:status:{ip}")

    @staticmethod
    async def cache_ip_data(ip: str, data: dict, expire: int = 300):
        r = await get_redis()
        await r.setex(f"ip:data:{ip}", expire, json.dumps(data, default=str))

    @staticmethod
    async def get_cached_ip_data(ip: str) -> Optional[dict]:
        r = await get_redis()
        d = await r.get(f"ip:data:{ip}")
        if d:
            return json.loads(d)
        return None
