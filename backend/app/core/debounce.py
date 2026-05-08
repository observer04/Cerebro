from typing import Any


async def redis_debounce(
    redis_client: Any, component_id: str, work_item_id: str, ttl_seconds: int = 10
) -> bool:
    key = f"debounce:{component_id}"
    result = await redis_client.set(key, work_item_id, nx=True, ex=ttl_seconds)
    return bool(result)
