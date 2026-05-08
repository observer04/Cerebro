from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WorkItemOut(BaseModel):
    id: UUID
    component_id: str
    severity: str
    status: str
    title: str
    assignee: str | None
    signal_count: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    mttr_seconds: float | None
