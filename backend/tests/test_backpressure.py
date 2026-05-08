from __future__ import annotations

import asyncio
import random

import pytest

from app.core.backpressure import async_retry


@pytest.mark.asyncio
async def test_succeeds_first_try_no_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []

    async def sleep_stub(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", sleep_stub)

    async def operation() -> str:
        return "ok"

    result = await async_retry(operation)

    assert result == "ok"
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_retries_twice_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    calls = 0

    async def sleep_stub(seconds: float) -> None:
        sleep_calls.append(seconds)

    async def operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("network")
        return "ok"

    monkeypatch.setattr(asyncio, "sleep", sleep_stub)
    monkeypatch.setattr(random, "uniform", lambda _a, _b: 0.05)

    result = await async_retry(operation, base_delay=0.1, max_delay=30.0)

    assert result == "ok"
    assert sleep_calls[0] == pytest.approx(0.105)
    assert sleep_calls[1] == pytest.approx(0.21)


@pytest.mark.asyncio
async def test_calls_on_failure_after_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    callback_calls = 0

    async def sleep_stub(seconds: float) -> None:
        sleep_calls.append(seconds)

    async def operation() -> str:
        raise TimeoutError("timeout")

    async def on_failure() -> None:
        nonlocal callback_calls
        callback_calls += 1

    monkeypatch.setattr(asyncio, "sleep", sleep_stub)
    monkeypatch.setattr(random, "uniform", lambda _a, _b: 0.0)

    with pytest.raises(TimeoutError):
        await async_retry(
            operation,
            max_retries=3,
            base_delay=0.01,
            max_delay=1.0,
            on_failure=on_failure,
        )

    assert callback_calls == 1
    assert len(sleep_calls) == 2


@pytest.mark.asyncio
async def test_jitter_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []

    async def sleep_stub(seconds: float) -> None:
        sleep_calls.append(seconds)

    async def operation() -> str:
        raise ConnectionError("network")

    monkeypatch.setattr(asyncio, "sleep", sleep_stub)
    monkeypatch.setattr(random, "uniform", lambda _a, _b: 0.1)

    with pytest.raises(ConnectionError):
        await async_retry(operation, max_retries=2, base_delay=1.0, max_delay=10.0)

    assert sleep_calls[0] == pytest.approx(1.1)
