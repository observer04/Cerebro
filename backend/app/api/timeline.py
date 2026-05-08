import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import mongodb, postgres

router = APIRouter(prefix="/api/v1", tags=["timeline"])
logger = logging.getLogger(__name__)


@router.get(
    "/work-items/{work_item_id}/timeline",
    summary="Incident timeline",
    description=(
        "Constructs a chronological event list by joining PostgreSQL work item data "
        "(creation, transitions, resolution, closure) with MongoDB signal burst aggregations."
    ),
    responses={404: {"description": "Work item not found."}},
)
async def get_work_item_timeline(work_item_id: UUID) -> dict:
    """Construct an incident timeline by joining PostgreSQL work item data with MongoDB signal bursts."""
    # Step 1: Get work item from PostgreSQL.
    async with postgres.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM work_items WHERE id = $1", work_item_id
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Work item not found")

    events = []
    work_item_id_str = str(work_item_id)

    # Event 1: Incident created
    events.append({
        "type": "created",
        "timestamp": row["created_at"].isoformat(),
        "label": f"Incident created — {row['component_id']}",
        "detail": f"Severity: {row['severity']}",
    })

    # Step 2: Get signal burst data from MongoDB for this work item.
    collection = mongodb.get_collection("raw_signals")
    pipeline = [
        {"$match": {"work_item_id": work_item_id_str}},
        {"$sort": {"timestamp": 1}},
        {"$group": {
            "_id": None,
            "first_signal": {"$first": "$timestamp"},
            "last_signal": {"$last": "$timestamp"},
            "count": {"$sum": 1},
            "sources": {"$addToSet": "$source"},
        }},
    ]
    try:
        cursor = collection.aggregate(pipeline)
        burst_data = await cursor.to_list(length=1)
        if burst_data:
            burst = burst_data[0]
            events.append({
                "type": "burst",
                "timestamp": str(burst["first_signal"]),
                "label": f"Signal burst — {burst['count']} signals",
                "detail": f"Sources: {', '.join(filter(None, burst['sources'][:5]))}",
                "signal_count": burst["count"],
            })
    except Exception:
        logger.warning("Failed to fetch signal burst for timeline")

    # Event 3: Status transitions (derived from current state).
    if row["assignee"]:
        events.append({
            "type": "transition",
            "timestamp": (row["updated_at"] or row["created_at"]).isoformat(),
            "label": f"Assigned to {row['assignee']}",
            "detail": f"Status: {row['status']}",
        })

    if row["resolved_at"]:
        events.append({
            "type": "transition",
            "timestamp": row["resolved_at"].isoformat(),
            "label": "Incident resolved",
            "detail": f"MTTR: {row['mttr_seconds']}s" if row["mttr_seconds"] else None,
        })

    # Event 4: RCA submitted (check if one exists).
    async with postgres.acquire() as conn:
        rca_row = await conn.fetchrow(
            "SELECT submitted_at FROM rca_records WHERE work_item_id = $1",
            work_item_id,
        )
    if rca_row:
        events.append({
            "type": "rca",
            "timestamp": rca_row["submitted_at"].isoformat(),
            "label": "RCA submitted",
        })

    if row["status"] == "CLOSED":
        events.append({
            "type": "closed",
            "timestamp": (row["updated_at"] or row["created_at"]).isoformat(),
            "label": "Incident closed",
        })

    # Sort events chronologically.
    events.sort(key=lambda e: e.get("timestamp", ""))

    return {"work_item_id": work_item_id_str, "events": events}
