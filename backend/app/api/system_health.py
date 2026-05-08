import logging

from fastapi import APIRouter

from app.config import settings
from app.db import postgres, redis_client

router = APIRouter(prefix="/api/v1", tags=["system-health"])
logger = logging.getLogger(__name__)


@router.get("/system/health-summary")
async def get_health_summary() -> dict:
    """O(1) system health snapshot using Redis counters and PostgreSQL aggregates."""
    redis = redis_client.get_client()

    # Redis O(1) reads
    throughput = await redis.get(settings.throughput_counter_key) or "0"
    debounce_active = await redis.get("debounce:active_count") or "0"

    # PostgreSQL aggregate — single efficient query
    pg_query = """
        SELECT
            COUNT(*) FILTER (WHERE status != 'CLOSED')::int AS active_incidents,
            COUNT(*) FILTER (WHERE status = 'OPEN')::int AS open_count,
            COUNT(*) FILTER (WHERE status = 'INVESTIGATING')::int AS investigating_count,
            COUNT(*) FILTER (WHERE status = 'RESOLVED')::int AS resolved_count,
            COUNT(*) FILTER (WHERE status = 'CLOSED')::int AS closed_count,
            COUNT(*) FILTER (WHERE severity = 'P0' AND status != 'CLOSED')::int AS p0_active,
            COUNT(*) FILTER (WHERE severity = 'P1' AND status != 'CLOSED')::int AS p1_active,
            COUNT(*) FILTER (WHERE severity = 'P2' AND status != 'CLOSED')::int AS p2_active,
            COUNT(*) FILTER (WHERE severity = 'P3' AND status != 'CLOSED')::int AS p3_active,
            ROUND(AVG(mttr_seconds) FILTER (WHERE mttr_seconds IS NOT NULL))::int AS avg_mttr
        FROM work_items
    """
    async with postgres.acquire() as conn:
        row = await conn.fetchrow(pg_query)

    return {
        "active_incidents": row["active_incidents"],
        "by_status": {
            "open": row["open_count"],
            "investigating": row["investigating_count"],
            "resolved": row["resolved_count"],
            "closed": row["closed_count"],
        },
        "by_severity": {
            "P0": row["p0_active"],
            "P1": row["p1_active"],
            "P2": row["p2_active"],
            "P3": row["p3_active"],
        },
        "avg_mttr_seconds": row["avg_mttr"],
        "throughput_total": int(throughput),
        "debounce_active_windows": int(debounce_active),
    }
