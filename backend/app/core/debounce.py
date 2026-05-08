from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.core.alert_strategy import COMPONENT_SEVERITY, execute_alert
from app.models.signal import SignalIn

WORK_ITEM_INSERT = (
    "INSERT INTO work_items "
    "(component_id, severity, status, title, signal_count, created_at, updated_at) "
    "VALUES ($1, $2, 'OPEN', $3, 1, $4, $4) RETURNING id"
)
WORK_ITEM_DELETE = "DELETE FROM work_items WHERE id = $1"
WORK_ITEM_INCREMENT = (
    "UPDATE work_items SET signal_count = signal_count + 1, updated_at = NOW() "
    "WHERE id = $1"
)


async def _create_work_item(pg_pool: Any, signal: SignalIn) -> str:
    severity = COMPONENT_SEVERITY[signal.component_id]
    title = f"Incident: {signal.component_id}"
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            WORK_ITEM_INSERT, signal.component_id, severity, title, signal.timestamp
        )
    return str(row["id"])


async def _delete_work_item(pg_pool: Any, work_item_id: str) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute(WORK_ITEM_DELETE, work_item_id)


async def _increment_signal_count(pg_pool: Any, work_item_id: str) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute(WORK_ITEM_INCREMENT, work_item_id)


async def debounce_and_process(
    signal: SignalIn, redis_client: Any, pg_pool: Any, mongo_db: Any | None = None
) -> str:
    work_item_id = await _create_work_item(pg_pool, signal)
    debounce_key = f"debounce:{signal.component_id}"

    result = await redis_client.set(debounce_key, work_item_id, nx=True, ex=10)
    if result:
        await execute_alert(
            SimpleNamespace(component_id=signal.component_id, title=signal.component_id)
        )
        return "created"

    existing_id = await redis_client.get(debounce_key)
    if existing_id is None:
        retry = await redis_client.set(debounce_key, work_item_id, nx=True, ex=10)
        if retry:
            await execute_alert(
                SimpleNamespace(
                    component_id=signal.component_id, title=signal.component_id
                )
            )
            return "created"
        existing_id = await redis_client.get(debounce_key)

    if existing_id:
        await _delete_work_item(pg_pool, work_item_id)
        await _increment_signal_count(pg_pool, str(existing_id))
        return "deduplicated"

    return "created"
