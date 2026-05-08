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


def create_app() -> FastAPI:
    app = FastAPI(title="IMS API", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(api_router)
    return app


app = create_app()
