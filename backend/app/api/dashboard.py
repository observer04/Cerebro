from fastapi import APIRouter

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
