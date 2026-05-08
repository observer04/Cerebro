from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.state_machine import (
    AssigneeRequiredError,
    InvalidTransitionError,
    RCARecord,
    RCARequiredError,
    WorkItem,
    WorkItemStateMachine,
)


def make_work_item(status: str = "OPEN", assignee: str | None = None) -> WorkItem:
    now = datetime.now(timezone.utc)
    return WorkItem(
        id=uuid4(),
        component_id="database",
        severity="P0",
        status=status,
        title="Database down",
        assignee=assignee,
        signal_count=1,
        created_at=now,
        updated_at=now,
    )


def test_open_to_investigating_succeeds() -> None:
    work_item = make_work_item(status="OPEN")
    machine = WorkItemStateMachine(work_item)

    updated = machine.transition_to("INVESTIGATING", assignee="oncall@corp.com")

    assert updated.status == "INVESTIGATING"
    assert updated.assignee == "oncall@corp.com"


def test_open_to_closed_invalid() -> None:
    work_item = make_work_item(status="OPEN")
    machine = WorkItemStateMachine(work_item)

    with pytest.raises(InvalidTransitionError):
        machine.transition_to("CLOSED")


def test_investigating_to_resolved_succeeds() -> None:
    work_item = make_work_item(status="OPEN")
    machine = WorkItemStateMachine(work_item)

    machine.transition_to("INVESTIGATING", assignee="oncall@corp.com")
    updated = machine.transition_to("RESOLVED")

    assert updated.status == "RESOLVED"
    assert updated.resolved_at is not None


def test_investigating_to_open_reopens() -> None:
    work_item = make_work_item(status="OPEN")
    machine = WorkItemStateMachine(work_item)

    machine.transition_to("INVESTIGATING", assignee="oncall@corp.com")
    updated = machine.transition_to("OPEN")

    assert updated.status == "OPEN"


def test_resolved_to_closed_without_rca_raises() -> None:
    work_item = make_work_item(status="RESOLVED")
    machine = WorkItemStateMachine(work_item)

    with pytest.raises(RCARequiredError):
        machine.transition_to("CLOSED")


def test_resolved_to_closed_with_rca_sets_mttr() -> None:
    created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    resolved_at = created_at + timedelta(hours=1)
    work_item = make_work_item(status="RESOLVED")
    work_item.created_at = created_at
    work_item.resolved_at = resolved_at
    machine = WorkItemStateMachine(work_item)

    rca = RCARecord(
        root_cause="Connection pool exhausted due to leak",
        mitigation="Restarted service and raised pool size",
        prevention="Add pool monitoring alert",
        submitted_by="oncall@corp.com",
        submitted_at=created_at + timedelta(hours=2),  # RCA submitted later — shouldn't affect MTTR
    )

    updated = machine.transition_to("CLOSED", rca=rca)

    assert updated.status == "CLOSED"
    assert updated.mttr_seconds == pytest.approx(3600.0)


def test_resolved_to_investigating_succeeds() -> None:
    work_item = make_work_item(status="RESOLVED")
    machine = WorkItemStateMachine(work_item)

    updated = machine.transition_to("INVESTIGATING", assignee="oncall@corp.com")

    assert updated.status == "INVESTIGATING"


def test_closed_is_terminal() -> None:
    work_item = make_work_item(status="CLOSED")
    machine = WorkItemStateMachine(work_item)

    with pytest.raises(InvalidTransitionError):
        machine.transition_to("OPEN")


def test_investigating_requires_assignee() -> None:
    work_item = make_work_item(status="OPEN")
    machine = WorkItemStateMachine(work_item)

    with pytest.raises(AssigneeRequiredError):
        machine.transition_to("INVESTIGATING")
