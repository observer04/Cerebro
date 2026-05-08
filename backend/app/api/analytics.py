import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.db import postgres

router = APIRouter(prefix="/api/v1", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get(
    "/analytics/throughput",
    summary="Throughput time-series",
)
async def get_throughput_analytics(
    interval: str = Query(default="1 hour", pattern=r"^\d+\s+(minute|hour|day)s?$"),
    hours: int = Query(default=24, ge=1, le=168),
) -> dict:
    """Time-series signal throughput from TimescaleDB's time_bucket aggregation."""
    throughput_query = """
        SELECT time_bucket($1::interval, time) AS period,
               ROUND(AVG(value))::int AS signals
        FROM metrics
        WHERE metric_name = 'signals_per_second'
          AND time >= NOW() - ($2 || ' hours')::interval
        GROUP BY period
        ORDER BY period ASC
    """
    incidents_query = """
        SELECT time_bucket($1::interval, created_at) AS period,
               COUNT(*)::int AS incidents
        FROM work_items
        WHERE created_at >= NOW() - ($2 || ' hours')::interval
        GROUP BY period
        ORDER BY period ASC
    """
    async with postgres.acquire() as conn:
        tp_rows = await conn.fetch(throughput_query, interval, str(hours))
        inc_rows = await conn.fetch(incidents_query, interval, str(hours))

    # Merge the two series by period
    inc_map = {row["period"]: row["incidents"] for row in inc_rows}
    return {
        "interval": interval,
        "hours": hours,
        "buckets": [
            {
                "period": row["period"].isoformat(),
                "signals": row["signals"],
                "incidents": inc_map.get(row["period"], 0),
            }
            for row in tp_rows
        ],
    }


@router.get(
    "/analytics/component-health",
    summary="Per-component health aggregation",
)
async def get_component_health() -> dict:
    """Cross-store aggregation: PostgreSQL for incident counts, TimescaleDB for throughput."""
    # Active incident counts per component from PostgreSQL.
    pg_query = """
        SELECT component_id,
               COUNT(*) FILTER (WHERE status != 'CLOSED')::int AS active_incidents,
               COUNT(*)::int AS total_incidents,
               ROUND(AVG(mttr_seconds) FILTER (WHERE mttr_seconds IS NOT NULL))::int AS avg_mttr,
               MAX(created_at) AS last_incident
        FROM work_items
        GROUP BY component_id
        ORDER BY active_incidents DESC, total_incidents DESC
    """
    async with postgres.acquire() as conn:
        rows = await conn.fetch(pg_query)

    components = []
    for row in rows:
        components.append({
            "component_id": row["component_id"],
            "active_incidents": row["active_incidents"],
            "total_incidents": row["total_incidents"],
            "avg_mttr_seconds": row["avg_mttr"],
            "last_incident": row["last_incident"].isoformat() if row["last_incident"] else None,
        })

    return {"components": components}
