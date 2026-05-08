import json
import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.utils import row_to_out, row_to_work_item
from app.core.state_machine import AssigneeRequiredError, InvalidTransitionError, WorkItemStateMachine
from app.db import postgres, redis_client
from app.models.work_item import WorkItemOut

router = APIRouter(prefix="/api/v1", tags=["work-items"])
logger = logging.getLogger(__name__)


class TransitionIn(BaseModel):
    target_status: str = Field(..., min_length=1)
    assignee: str | None = None


@router.get("/work-items", response_model=List[WorkItemOut])
async def list_work_items(
    status: str | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> List[WorkItemOut]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    conditions: list[str] = []
    values: list[object] = []

    if status:
        values.append(status)
        conditions.append(f"status = ${len(values)}")
    if severity:
        values.append(severity)
        conditions.append(f"severity = ${len(values)}")

    query = "SELECT * FROM work_items"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    limit_idx = len(values) + 1
    offset_idx = len(values) + 2
    values.append(page_size)
    values.append(offset)
    query += f" ORDER BY created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}"

    async with postgres.acquire() as conn:
        rows = await conn.fetch(query, *values)

    return [row_to_out(row) for row in rows]


@router.get("/work-items/{work_item_id}", response_model=WorkItemOut)
async def get_work_item(work_item_id: UUID) -> WorkItemOut:
    async with postgres.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM work_items WHERE id = $1", work_item_id
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Work item not found")

    return row_to_out(row)


@router.patch("/work-items/{work_item_id}/transition")
async def transition_work_item(work_item_id: UUID, payload: TransitionIn) -> dict:
    async with postgres.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM work_items WHERE id = $1 FOR UPDATE", work_item_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Work item not found")

        work_item = row_to_work_item(row)
        machine = WorkItemStateMachine(work_item)
        previous_status = work_item.status

        try:
            updated = machine.transition_to(
                payload.target_status, assignee=payload.assignee
            )
        except InvalidTransitionError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "InvalidTransition",
                    "message": str(exc),
                    "allowed_transitions": exc.allowed_transitions,
                },
            )
        except AssigneeRequiredError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        await conn.execute(
            "UPDATE work_items SET status = $1, assignee = $2, resolved_at = $3, "
            "mttr_seconds = $4, updated_at = $5 WHERE id = $6",
            updated.status,
            updated.assignee,
            updated.resolved_at,
            updated.mttr_seconds,
            updated.updated_at or datetime.now(timezone.utc),
            work_item_id,
        )

    try:
        redis = redis_client.get_client()
        await redis.publish(
            "incidents",
            json.dumps(
                {
                    "type": "incident.transitioned",
                    "data": {
                        "id": str(work_item_id),
                        "status": updated.status,
                        "previous_status": previous_status,
                    },
                }
            ),
        )
    except Exception:
        logger.exception("Failed to publish transition event")

    return {
        "id": str(work_item_id),
        "status": updated.status,
        "previous_status": previous_status,
        "transitioned_at": updated.updated_at,
    }
