from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID


class InvalidTransitionError(ValueError):
    def __init__(self, current: str, target: str, allowed: List[str]) -> None:
        super().__init__(f"Cannot transition from {current} to {target}")
        self.current = current
        self.target = target
        self.allowed_transitions = allowed


class AssigneeRequiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("Assignee required for INVESTIGATING")


class RCARequiredError(ValueError):
    def __init__(self) -> None:
        super().__init__("RCA required to close work item")


@dataclass
class RCARecord:
    root_cause: str
    mitigation: str
    prevention: str
    submitted_by: str
    submitted_at: datetime


@dataclass
class WorkItem:
    id: UUID
    component_id: str
    severity: str
    status: str
    title: str
    assignee: Optional[str]
    signal_count: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None
    rca: Optional[RCARecord] = None

    def has_complete_rca(self) -> bool:
        if self.rca is None:
            return False
        return all(
            [
                self.rca.root_cause,
                self.rca.mitigation,
                self.rca.prevention,
                self.rca.submitted_at,
            ]
        )


class IncidentState(ABC):
    name: str

    @abstractmethod
    def allowed_transitions(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def on_enter(self, work_item: WorkItem) -> None:
        raise NotImplementedError

    def validate_transition(self, target_state: str, work_item: WorkItem) -> None:
        allowed = self.allowed_transitions()
        if target_state not in allowed:
            raise InvalidTransitionError(self.name, target_state, allowed)


class OpenState(IncidentState):
    name = "OPEN"

    def allowed_transitions(self) -> List[str]:
        return ["INVESTIGATING", "RESOLVED"]

    def on_enter(self, work_item: WorkItem) -> None:
        return None


class InvestigatingState(IncidentState):
    name = "INVESTIGATING"

    def allowed_transitions(self) -> List[str]:
        return ["RESOLVED", "OPEN"]

    def on_enter(self, work_item: WorkItem) -> None:
        if not work_item.assignee:
            raise AssigneeRequiredError()


class ResolvedState(IncidentState):
    name = "RESOLVED"

    def allowed_transitions(self) -> List[str]:
        return ["CLOSED", "INVESTIGATING"]

    def on_enter(self, work_item: WorkItem) -> None:
        work_item.resolved_at = datetime.now(timezone.utc)


class ClosedState(IncidentState):
    name = "CLOSED"

    def allowed_transitions(self) -> List[str]:
        return []

    def on_enter(self, work_item: WorkItem) -> None:
        if not work_item.has_complete_rca():
            raise RCARequiredError()
        mttr = work_item.resolved_at - work_item.created_at
        work_item.mttr_seconds = mttr.total_seconds()


STATE_MAP = {
    "OPEN": OpenState,
    "INVESTIGATING": InvestigatingState,
    "RESOLVED": ResolvedState,
    "CLOSED": ClosedState,
}


class WorkItemStateMachine:
    def __init__(self, work_item: WorkItem) -> None:
        self.work_item = work_item
        self.state = STATE_MAP[work_item.status]()

    def transition_to(
        self,
        target_status: str,
        rca: Optional[RCARecord] = None,
        assignee: Optional[str] = None,
    ) -> WorkItem:
        self.state.validate_transition(target_status, self.work_item)
        if assignee is not None:
            self.work_item.assignee = assignee
        if rca is not None:
            self.work_item.rca = rca

        new_state = STATE_MAP[target_status]()
        new_state.on_enter(self.work_item)
        self.work_item.status = target_status
        self.work_item.updated_at = datetime.now(timezone.utc)
        self.state = new_state
        return self.work_item

    def allowed_transitions(self) -> List[str]:
        return self.state.allowed_transitions()
