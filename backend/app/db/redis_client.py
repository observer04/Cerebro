import redis.asyncio as redis

from app.config import settings

_client: redis.Redis | None = None


async def init_pool() -> None:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)


async def close_pool() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def get_client() -> redis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialized")
    return _client
