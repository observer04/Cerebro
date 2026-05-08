from app.core.state_machine import WorkItem
from app.models.work_item import WorkItemOut


def row_to_work_item(row) -> WorkItem:
    return WorkItem(
        id=row["id"],
        component_id=row["component_id"],
        severity=row["severity"],
        status=row["status"],
        title=row["title"],
        assignee=row["assignee"],
        signal_count=row["signal_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        resolved_at=row["resolved_at"],
        mttr_seconds=row["mttr_seconds"],
    )


def row_to_out(row) -> WorkItemOut:
    return WorkItemOut(**dict(row))
