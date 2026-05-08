from __future__ import annotations

import asyncio
import random
from typing import Any, Awaitable, Callable, TypeVar

import asyncpg
from pymongo.errors import PyMongoError

T = TypeVar("T")


async def async_retry(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 30.0,
    on_failure: Callable[[], Any] | None = None,
) -> T:
    for attempt in range(max_retries):
        try:
            return await operation()
        except (ConnectionError, TimeoutError, asyncpg.PostgresError, PyMongoError):
            if attempt == max_retries - 1:
                if on_failure is not None:
                    result = on_failure()
                    if asyncio.iscoroutine(result):
                        await result
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            jitter = delay * random.uniform(-0.1, 0.1)
            await asyncio.sleep(delay + jitter)

    raise RuntimeError("async_retry exhausted without raising")
