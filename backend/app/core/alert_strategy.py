import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AlertStrategy(ABC):
    @abstractmethod
    async def execute(self, work_item) -> None:
        raise NotImplementedError


class PagerDutyAlertStrategy(AlertStrategy):
    async def execute(self, work_item) -> None:
        logger.info("PagerDuty alert for %s", work_item.component_id)


class SlackUrgentAlertStrategy(AlertStrategy):
    async def execute(self, work_item) -> None:
        logger.info("Urgent Slack alert for %s", work_item.component_id)


class SlackAlertStrategy(AlertStrategy):
    async def execute(self, work_item) -> None:
        logger.info("Slack alert for %s", work_item.component_id)


class LogOnlyAlertStrategy(AlertStrategy):
    async def execute(self, work_item) -> None:
        logger.info("Log-only alert for %s", work_item.component_id)


ALERT_STRATEGIES = {
    "P0": PagerDutyAlertStrategy(),
    "P1": SlackUrgentAlertStrategy(),
    "P2": SlackAlertStrategy(),
    "P3": LogOnlyAlertStrategy(),
}

COMPONENT_SEVERITY = {
    "database": "P0",
    "api_gateway": "P1",
    "cache": "P2",
    "cdn": "P3",
}


def get_strategy_for_component(component_id: str) -> AlertStrategy:
    severity = COMPONENT_SEVERITY[component_id]
    return ALERT_STRATEGIES[severity]


async def execute_alert(work_item) -> None:
    strategy = get_strategy_for_component(work_item.component_id)
    await strategy.execute(work_item)
