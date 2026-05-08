import os
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("RATE_LIMIT_PER_IP", "10/second")
os.environ.setdefault("RATE_LIMIT_GLOBAL", "10000/second")

from app.config import settings
from app.main import create_app


@pytest_asyncio.fixture
async def client():
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset_state():
    conn = await asyncpg.connect(settings.postgres_dsn)
    await conn.execute("TRUNCATE work_items, rca_records, metrics")
    await conn.close()

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.flushdb()
    await redis_client.close()

    yield


async def insert_work_item(status: str) -> UUID:
    conn = await asyncpg.connect(settings.postgres_dsn)
    now = datetime.utcnow()
    resolved_at = now if status == "RESOLVED" else None
    work_item_id = uuid4()

    await conn.execute(
        "INSERT INTO work_items (id, component_id, severity, status, title, assignee, "
        "signal_count, created_at, updated_at, resolved_at, mttr_seconds) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        work_item_id,
        "database",
        "P0",
        status,
        "Database down",
        None,
        1,
        now,
        now,
        resolved_at,
        None,
    )
    await conn.close()
    return work_item_id


@pytest.mark.asyncio
async def test_signal_ingestion_returns_202(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/signals", json={"component_id": "database", "source": "test"}
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429(client: AsyncClient) -> None:
    responses = []
    for _ in range(11):
        responses.append(
            await client.post(
                "/api/v1/signals",
                json={"component_id": "database", "source": "test"},
            )
        )

    assert responses[-1].status_code == 429


@pytest.mark.asyncio
async def test_get_work_items_returns_paginated(client: AsyncClient) -> None:
    await insert_work_item("OPEN")

    response = await client.get("/api/v1/work-items")

    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_transition_invalid_returns_409(client: AsyncClient) -> None:
    work_item_id = await insert_work_item("OPEN")

    response = await client.patch(
        f"/api/v1/work-items/{work_item_id}/transition",
        json={"target_status": "CLOSED"},
    )

    assert response.status_code == 409
    assert "allowed_transitions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rca_root_cause_too_short_returns_422(client: AsyncClient) -> None:
    work_item_id = await insert_work_item("RESOLVED")

    response = await client.post(
        f"/api/v1/work-items/{work_item_id}/rca",
        json={
            "root_cause": "too short",
            "mitigation": "Restarted service",
            "prevention": "Add monitoring",
            "submitted_by": "oncall@corp.com",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rca_on_resolved_returns_201(client: AsyncClient) -> None:
    work_item_id = await insert_work_item("RESOLVED")

    response = await client.post(
        f"/api/v1/work-items/{work_item_id}/rca",
        json={
            "root_cause": "Connection pool exhausted due to leak",
            "mitigation": "Restarted service and increased pool size",
            "prevention": "Add pool monitoring alert",
            "submitted_by": "oncall@corp.com",
        },
    )

    assert response.status_code == 201
    assert response.json()["mttr_seconds"] is not None


@pytest.mark.asyncio
async def test_health_returns_component_status(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert "components" in payload
    assert "kafka" in payload["components"]
    assert "redis" in payload["components"]
    assert "mongodb" in payload["components"]
    assert "postgresql" in payload["components"]
