from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import api_router
from app.api.rate_limit import limiter
from app.config import settings
from app.db import kafka as kafka_db
from app.db import mongodb, postgres, redis_client

logger = logging.getLogger("uvicorn.error")


async def throughput_logger(app: FastAPI) -> None:
    window = app.state.throughput_window_seconds
    counter_key = settings.throughput_counter_key
    rate_key = settings.throughput_rate_key
    lock_key = settings.throughput_lock_key
    lock_ttl = max(int(window) + 1, 2)
    while not app.state.stop_event.is_set():
        try:
            await asyncio.wait_for(app.state.stop_event.wait(), timeout=window)
            break  # stop_event was set during the wait
        except asyncio.TimeoutError:
            pass  # normal: window elapsed, compute metrics
        try:
            redis = redis_client.get_client()
            lock_token = str(uuid.uuid4())
            acquired = await redis.set(lock_key, lock_token, nx=True, ex=lock_ttl)
            if not acquired:
                continue

            try:
                raw_count = await redis.getset(counter_key, 0)
                try:
                    count = int(raw_count) if raw_count else 0
                except (TypeError, ValueError):
                    count = 0

                rate = count / window if window else 0.0
                app.state.last_throughput = rate
                await redis.setex(rate_key, max(int(window * 2), 1), rate)
                logger.info("[THROUGHPUT] %.1f signals/sec", rate)

                try:
                    await redis.publish(
                        "incidents",
                        json.dumps(
                            {
                                "type": "metrics.throughput",
                                "data": {"signals_per_second": rate},
                            }
                        ),
                    )
                except Exception:
                    logger.exception("Failed to publish throughput event")

                try:
                    async with postgres.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO metrics (time, metric_name, value, labels) "
                            "VALUES (NOW(), $1, $2, $3)",
                            "signals_per_second",
                            rate,
                            json.dumps({}),
                        )
                except Exception:
                    logger.exception("Failed to write throughput metric")
            finally:
                current_token = await redis.get(lock_key)
                if current_token == lock_token:
                    await redis.delete(lock_key)
        except Exception:
            logger.exception("Failed to compute throughput metric")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await postgres.init_pool()
    await mongodb.init_pool()
    await redis_client.init_pool()
    await kafka_db.init_producer()

    app.state.last_throughput = 0.0
    app.state.throughput_window_seconds = settings.throughput_window_seconds
    app.state.start_time = time.monotonic()
    app.state.stop_event = asyncio.Event()
    app.state.throughput_task = asyncio.create_task(throughput_logger(app))

    try:
        yield
    finally:
        app.state.stop_event.set()
        await app.state.throughput_task
        await kafka_db.close_producer()
        await redis_client.close_pool()
        await mongodb.close_pool()
        await postgres.close_pool()


OPENAPI_TAGS = [
    {
        "name": "signals",
        "description": "**Signal Ingestion** — Accept failure signals from monitoring agents and queue them to Kafka for async processing.",
    },
    {
        "name": "work-items",
        "description": "**Incident Work Items** — CRUD and state-machine transitions for deduplicated incidents.",
    },
    {
        "name": "rca",
        "description": "**Root Cause Analysis** — Submit RCA to close incidents. Enforces min-length and completeness gates.",
    },
    {
        "name": "dashboard",
        "description": "**Dashboard & SSE** — Active incidents, metrics, and a Server-Sent Events stream for real-time updates.",
    },
    {
        "name": "analytics",
        "description": "**Analytics** — TimescaleDB-powered throughput time-series and per-component health aggregations.",
    },
    {
        "name": "system-health",
        "description": "**System Health** — O(1) snapshot of active incidents, severity breakdown, MTTR, and debounce windows.",
    },
    {
        "name": "timeline",
        "description": "**Incident Timeline** — Cross-store join of PostgreSQL work items and MongoDB signal bursts into a chronological event list.",
    },
    {
        "name": "signals-query",
        "description": "**Signal Query** — Retrieve raw signals from MongoDB linked to a specific work item.",
    },
    {
        "name": "health",
        "description": "**Infrastructure Health** — Liveness probes for Kafka, Redis, MongoDB, and PostgreSQL with throughput metrics.",
    },
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="IMS — Incident Management System",
        summary="Real-time failure signal ingestion, incident deduplication, and dashboard API.",
        description=(
            "## Overview\n\n"
            "IMS ingests failure signals from distributed monitoring agents, deduplicates them "
            "into incident work items using a Redis-based debounce algorithm, and serves a "
            "real-time React dashboard via Server-Sent Events.\n\n"
            "### Key Concepts\n\n"
            "- **Signals** are raw failure events produced by health-checkers.\n"
            "- **Work Items** are deduplicated incidents with a state machine "
            "(OPEN → INVESTIGATING → RESOLVED → CLOSED).\n"
            "- **RCA** (Root Cause Analysis) is required before closing an incident.\n"
            "- **Backpressure** is handled at 5 layers: rate limiter → Kafka producer → "
            "Kafka retention → MongoDB retry → PostgreSQL retry.\n\n"
            "### Infrastructure\n\n"
            "| Service | Purpose |\n"
            "|---|---|\n"
            "| Kafka | Durable signal buffer (topic: `signals`, 6 partitions) |\n"
            "| Redis | Debounce state (`SET NX EX`), dashboard cache, SSE pub/sub |\n"
            "| MongoDB | Raw signal archive (append-only) |\n"
            "| PostgreSQL + TimescaleDB | Work items, RCA records, metrics hypertable |\n"
        ),
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(api_router)
    return app


app = create_app()
