from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.debounce import debounce_and_process
from app.models.signal import SignalIn


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._exp: dict[str, float] = {}
        self._time = 0.0
        self._lock = asyncio.Lock()

    def advance(self, seconds: float) -> None:
        self._time += seconds

    def _purge_expired(self, key: str) -> None:
        expiry = self._exp.get(key)
        if expiry is not None and self._time >= expiry:
            self._store.pop(key, None)
            self._exp.pop(key, None)

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        async with self._lock:
            self._purge_expired(key)
            if nx and key in self._store:
                return None
            self._store[key] = value
            if ex is not None:
                self._exp[key] = self._time + float(ex)
            return True

    async def get(self, key: str) -> str | None:
        self._purge_expired(key)
        return self._store.get(key)


class FakeConn:
    def __init__(self, pool: "FakePGPool") -> None:
        self.pool = pool

    async def fetchrow(self, query: str, *args):
        if "INSERT INTO work_items" in query:
            work_item_id = str(uuid4())
            self.pool.work_items[work_item_id] = {
                "id": work_item_id,
                "component_id": args[0],
                "signal_count": 1,
            }
            return {"id": work_item_id}
        raise ValueError("Unexpected query")

    async def execute(self, query: str, *args):
        if query.startswith("UPDATE work_items SET signal_count"):
            item = self.pool.work_items[str(args[0])]
            item["signal_count"] += 1
            return "UPDATE 1"
        raise ValueError("Unexpected query")


class FakePGPool:
    def __init__(self) -> None:
        self.work_items: dict[str, dict] = {}

    @asynccontextmanager
    async def acquire(self):
        yield FakeConn(self)


def make_signal(component_id: str = "database") -> SignalIn:
    return SignalIn(
        signal_id=uuid4(),
        component_id=component_id,
        timestamp=datetime.now(timezone.utc),
        severity_hint=None,
        source="test",
        metadata={},
    )


@pytest.mark.asyncio
async def test_first_signal_creates_work_item() -> None:
    redis = FakeRedis()
    pg_pool = FakePGPool()

    outcome, work_item_id = await debounce_and_process(make_signal(), redis, pg_pool, None)

    assert outcome == "created"
    assert work_item_id is not None
    assert len(pg_pool.work_items) == 1


@pytest.mark.asyncio
async def test_second_signal_deduplicates_and_increments() -> None:
    redis = FakeRedis()
    pg_pool = FakePGPool()

    _, first_id = await debounce_and_process(make_signal(), redis, pg_pool, None)
    outcome, second_id = await debounce_and_process(make_signal(), redis, pg_pool, None)

    assert outcome == "deduplicated"
    assert second_id == first_id
    assert pg_pool.work_items[first_id]["signal_count"] == 2


@pytest.mark.asyncio
async def test_window_expiry_creates_new_item() -> None:
    redis = FakeRedis()
    pg_pool = FakePGPool()

    _, old_id = await debounce_and_process(make_signal(), redis, pg_pool, None)

    redis.advance(11)
    outcome, new_id = await debounce_and_process(make_signal(), redis, pg_pool, None)

    assert outcome == "created"
    assert old_id != new_id
    assert len(pg_pool.work_items) == 2


@pytest.mark.asyncio
async def test_concurrent_signals_single_winner() -> None:
    redis = FakeRedis()
    pg_pool = FakePGPool()

    results = await asyncio.gather(
        debounce_and_process(make_signal(), redis, pg_pool, None),
        debounce_and_process(make_signal(), redis, pg_pool, None),
    )

    outcomes = [r[0] for r in results]
    assert outcomes.count("created") == 1
    assert outcomes.count("deduplicated") == 1
    # Only one work item created — no orphans
    assert len(pg_pool.work_items) == 1


@pytest.mark.asyncio
async def test_signal_count_matches_total() -> None:
    redis = FakeRedis()
    pg_pool = FakePGPool()

    _, work_item_id = await debounce_and_process(make_signal(), redis, pg_pool, None)
    for _ in range(4):
        await debounce_and_process(make_signal(), redis, pg_pool, None)

    assert pg_pool.work_items[work_item_id]["signal_count"] == 5

