import asyncio
import time
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.utils import row_to_out
from app.db import postgres, redis_client

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/active")
async def dashboard_active():
    redis = redis_client.get_client()
    cached = await redis.zrevrange("dashboard:active_incidents", 0, 49)
    if cached:
        return cached

    async with postgres.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM work_items WHERE status != 'CLOSED' ORDER BY created_at DESC LIMIT 50"
        )

    return [row_to_out(row) for row in rows]


@router.get("/dashboard/metrics")
async def dashboard_metrics():
    async with postgres.acquire() as conn:
        rows = await conn.fetch(
            "SELECT time, metric_name, value, labels FROM metrics ORDER BY time DESC LIMIT 100"
        )

    return [dict(row) for row in rows]


async def _event_generator(request: Request) -> AsyncIterator[str]:
    redis = redis_client.get_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe("incidents")

    last_keepalive = time.monotonic()

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message.get("type") == "message":
                payload = message.get("data")
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")
                yield f"data: {payload}\n\n"

            now = time.monotonic()
            if now - last_keepalive >= 15:
                yield ": keep-alive\n\n"
                last_keepalive = now

            await asyncio.sleep(0)
    finally:
        await pubsub.unsubscribe("incidents")
        await pubsub.close()


@router.get("/stream/events")
async def stream_events(request: Request):
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )
