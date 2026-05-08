import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db import mongodb, postgres

router = APIRouter(prefix="/api/v1", tags=["signals-query"])
logger = logging.getLogger(__name__)


@router.get(
    "/work-items/{work_item_id}/signals",
    summary="Get raw signals for a work item",
    description=(
        "Retrieve raw signals from MongoDB linked to a specific work item. "
        "Primary lookup uses `work_item_id` tag; falls back to `component_id` + timestamp range for legacy data."
    ),
    responses={404: {"description": "Work item not found."}},
)
async def get_work_item_signals(
    work_item_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> dict:
    """Retrieve raw signals from MongoDB for a specific work item."""
    # Verify work item exists in PostgreSQL.
    async with postgres.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT component_id, created_at, resolved_at FROM work_items WHERE id = $1",
            work_item_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Work item not found")

    collection = mongodb.get_collection("raw_signals")
    work_item_id_str = str(work_item_id)

    # Primary filter: work_item_id tag (set by consumer post-debounce).
    query_filter = {"work_item_id": work_item_id_str}
    total = await collection.count_documents(query_filter)

    # Fallback: if no tagged signals exist (legacy data), use component_id + timestamp range.
    if total == 0:
        fallback_filter: dict = {"component_id": row["component_id"]}
        if row["created_at"]:
            fallback_filter["timestamp"] = {"$gte": row["created_at"].isoformat()}
        if row["resolved_at"]:
            fallback_filter.setdefault("timestamp", {})
            fallback_filter["timestamp"]["$lte"] = row["resolved_at"].isoformat()
        total = await collection.count_documents(fallback_filter)
        query_filter = fallback_filter

    cursor = (
        collection.find(query_filter, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    signals = await cursor.to_list(length=limit)

    return {
        "signals": signals,
        "total": total,
        "limit": limit,
        "skip": skip,
    }
