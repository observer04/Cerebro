from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core import alert_strategy
from app.core.alert_strategy import (
    LogOnlyAlertStrategy,
    PagerDutyAlertStrategy,
    SlackAlertStrategy,
    SlackUrgentAlertStrategy,
)


def test_p0_component_selects_pagerduty() -> None:
    strategy = alert_strategy.get_strategy_for_component("database")
    assert isinstance(strategy, PagerDutyAlertStrategy)


def test_p1_component_selects_slack_urgent() -> None:
    strategy = alert_strategy.get_strategy_for_component("api_gateway")
    assert isinstance(strategy, SlackUrgentAlertStrategy)


def test_unknown_component_defaults_to_log_only() -> None:
    strategy = alert_strategy.get_strategy_for_component("unknown")
    assert isinstance(strategy, LogOnlyAlertStrategy)


@pytest.mark.asyncio
async def test_execute_alert_calls_strategy_once(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubStrategy(alert_strategy.AlertStrategy):
        def __init__(self) -> None:
            self.calls = 0

        async def execute(self, work_item) -> None:
            self.calls += 1

    stub = StubStrategy()
    monkeypatch.setitem(alert_strategy.ALERT_STRATEGIES, "P0", stub)
    monkeypatch.setitem(alert_strategy.COMPONENT_SEVERITY, "database", "P0")

    work_item = SimpleNamespace(component_id="database")

    await alert_strategy.execute_alert(work_item)

    assert stub.calls == 1
