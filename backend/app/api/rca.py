from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.utils import row_to_work_item
from app.core.state_machine import RCARecord, RCARequiredError, WorkItemStateMachine
from app.db import postgres
from app.models.rca import RCAIn

router = APIRouter(prefix="/api/v1", tags=["rca"])


@router.post("/work-items/{work_item_id}/rca", status_code=status.HTTP_201_CREATED)
async def submit_rca(work_item_id: UUID, payload: RCAIn) -> dict:
    async with postgres.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM work_items WHERE id = $1 FOR UPDATE", work_item_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Work item not found")
        if row["status"] != "RESOLVED":
            raise HTTPException(
                status_code=409,
                detail="Work item must be RESOLVED to accept RCA",
            )

        submitted_at = datetime.now(timezone.utc)
        await conn.execute(
            "INSERT INTO rca_records (work_item_id, root_cause, mitigation, prevention, "
            "submitted_by, submitted_at) VALUES ($1, $2, $3, $4, $5, $6)",
            work_item_id,
            payload.root_cause,
            payload.mitigation,
            payload.prevention,
            payload.submitted_by,
            submitted_at,
        )

        work_item = row_to_work_item(row)
        work_item.rca = RCARecord(
            root_cause=payload.root_cause,
            mitigation=payload.mitigation,
            prevention=payload.prevention,
            submitted_by=payload.submitted_by,
            submitted_at=submitted_at,
        )

        try:
            updated = WorkItemStateMachine(work_item).transition_to("CLOSED", rca=work_item.rca)
        except RCARequiredError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

        await conn.execute(
            "UPDATE work_items SET status = $1, resolved_at = $2, mttr_seconds = $3, "
            "updated_at = $4 WHERE id = $5",
            updated.status,
            updated.resolved_at,
            updated.mttr_seconds,
            updated.updated_at,
            work_item_id,
        )

    return {
        "id": str(work_item_id),
        "status": updated.status,
        "mttr_seconds": updated.mttr_seconds,
        "rca": {
            "root_cause": payload.root_cause,
            "mitigation": payload.mitigation,
            "prevention": payload.prevention,
            "submitted_by": payload.submitted_by,
            "submitted_at": submitted_at.isoformat(),
        },
    }
