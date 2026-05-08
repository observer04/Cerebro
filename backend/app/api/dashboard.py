import asyncio
import time
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.utils import row_to_out
from app.db import postgres, redis_client

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get(
    "/dashboard/active",
    summary="Active incidents",
    description="Returns up to 50 active (non-CLOSED) incidents. Reads from Redis sorted set cache first, falls back to PostgreSQL.",
)
async def dashboard_active():
    """O(1) Redis cache read for active incidents, with PostgreSQL fallback."""
    redis = redis_client.get_client()
    cached = await redis.zrevrange("dashboard:active_incidents", 0, 49)
    if cached:
        return cached

    async with postgres.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM work_items WHERE status != 'CLOSED' ORDER BY created_at DESC LIMIT 50"
        )

    return [row_to_out(row) for row in rows]


@router.get(
    "/dashboard/metrics",
    summary="Recent metrics",
    description="Returns the 100 most recent metric entries from the TimescaleDB `metrics` hypertable (signals_per_second, active_incidents, mttr_seconds).",
)
async def dashboard_metrics():
    """Fetch recent time-series metrics from TimescaleDB."""
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
                last_keepalive = time.monotonic()
                continue

            now = time.monotonic()
            if now - last_keepalive >= 15:
                yield ": keep-alive\n\n"
                last_keepalive = now
    finally:
        await pubsub.unsubscribe("incidents")
        await pubsub.close()


@router.get(
    "/stream/events",
    summary="SSE live event stream",
    description=(
        "Server-Sent Events endpoint for real-time dashboard updates. "
        "Subscribes to Redis Pub/Sub channel `incidents` and streams events as `data: {json}`.\n\n"
        "**Event types:** `incident.created`, `incident.updated`, `incident.transitioned`, "
        "`incident.closed`, `metrics.throughput`.\n\n"
        "Keep-alive comments sent every 15s. `X-Accel-Buffering: no` header prevents Nginx buffering."
    ),
)
async def stream_events(request: Request):
    """SSE endpoint — streams real-time incident and metrics events via Redis Pub/Sub."""
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )
