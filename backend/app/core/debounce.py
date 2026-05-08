from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.core.alert_strategy import execute_alert
from app.models.signal import SignalIn

WORK_ITEM_INSERT = (
    "INSERT INTO work_items "
    "(component_id, severity, status, title, signal_count, created_at, updated_at) "
    "VALUES ($1, $2, 'OPEN', $3, 1, $4, $4) RETURNING id"
)
WORK_ITEM_INCREMENT = (
    "UPDATE work_items SET signal_count = signal_count + 1, updated_at = NOW() "
    "WHERE id = $1"
)


async def _create_work_item(pg_pool: Any, signal: SignalIn, severity: str) -> str:
    title = f"Incident: {signal.component_id}"
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            WORK_ITEM_INSERT, signal.component_id, severity, title, signal.timestamp
        )
    return str(row["id"])


async def _increment_signal_count(pg_pool: Any, work_item_id: str) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute(WORK_ITEM_INCREMENT, work_item_id)


async def debounce_and_process(
    signal: SignalIn, redis_client: Any, pg_pool: Any, mongo_db: Any | None = None
) -> tuple[str, str]:
    from app.core.alert_strategy import COMPONENT_SEVERITY

    debounce_key = f"debounce:{signal.component_id}"
    severity = COMPONENT_SEVERITY.get(signal.component_id, "P3")

    # Step 1: Attempt to claim the debounce window atomically.
    # Use a temporary placeholder — we don't have a work item ID yet.
    placeholder = str(uuid4())
    claimed = await redis_client.set(debounce_key, placeholder, nx=True, ex=10)

    if claimed:
        # Winner: create the work item, then overwrite placeholder with real ID.
        work_item_id = await _create_work_item(pg_pool, signal, severity)
        await redis_client.set(debounce_key, work_item_id, ex=10)
        await execute_alert(
            SimpleNamespace(component_id=signal.component_id, title=signal.component_id)
        )
        return ("created", work_item_id)

    # Loser: increment the existing work item's signal count.
    existing_id = await redis_client.get(debounce_key)
    if existing_id and existing_id != placeholder:
        await _increment_signal_count(pg_pool, str(existing_id))
    return ("deduplicated", str(existing_id) if existing_id else "")
