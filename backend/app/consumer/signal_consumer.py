from __future__ import annotations

import asyncio
import json
import logging
import signal
from typing import Any

from aiokafka import TopicPartition

from app.config import settings
from app.core.backpressure import async_retry
from app.core.debounce import debounce_and_process
from app.db import kafka as kafka_db
from app.db import mongodb, postgres, redis_client
from app.models.signal import SignalIn

logger = logging.getLogger(__name__)

# Shared shutdown event — set by SIGTERM/SIGINT handlers for graceful exit.
shutdown_event = asyncio.Event()


async def _insert_raw_signal(mongo_db: Any, signal: SignalIn) -> None:
    collection = mongo_db["raw_signals"]

    async def operation() -> None:
        await collection.insert_one(signal.model_dump(mode="json"))

    await async_retry(operation)


async def _start_consumer_with_retry(
    consumer: Any, max_attempts: int = 10, base_delay: float = 2.0
) -> None:
    """Attempt to start the Kafka consumer with exponential backoff.

    This handles the common scenario where the worker container starts
    before Kafka is fully ready to accept connections.
    """
    for attempt in range(max_attempts):
        try:
            await consumer.start()
            logger.info("Kafka consumer started successfully")
            return
        except Exception:
            if attempt == max_attempts - 1:
                raise
            delay = min(base_delay * (2**attempt), 60.0)
            logger.warning(
                "Kafka not ready, retrying in %.1fs (attempt %d/%d)",
                delay,
                attempt + 1,
                max_attempts,
            )
            await asyncio.sleep(delay)


async def run() -> None:
    await postgres.init_pool()
    await mongodb.init_pool()
    await redis_client.init_pool()

    consumer = kafka_db.create_consumer("signals", "ims-workers")
    try:
        await _start_consumer_with_retry(consumer)
    except Exception:
        logger.exception("Kafka consumer failed to start after retries")
        await redis_client.close_pool()
        await mongodb.close_pool()
        await postgres.close_pool()
        return

    redis = redis_client.get_client()
    mongo_db = mongodb.get_db()
    pg_pool = postgres.get_pool()

    try:
        async for msg in consumer:
            if shutdown_event.is_set():
                break

            try:
                payload = json.loads(msg.value.decode("utf-8"))
                signal_in = SignalIn(**payload)
                await redis.incr(settings.throughput_counter_key)
                await _insert_raw_signal(mongo_db, signal_in)
                outcome = await debounce_and_process(signal_in, redis, pg_pool, mongo_db)
                event_type = (
                    "incident.created" if outcome == "created" else "incident.updated"
                )
                event = {
                    "type": event_type,
                    "data": {"component_id": signal_in.component_id},
                }
                await redis.publish("incidents", json.dumps(event))

                # Commit only after all downstream writes succeeded,
                # scoped to the specific partition/offset to prevent data loss.
                tp = TopicPartition(msg.topic, msg.partition)
                await consumer.commit({tp: msg.offset + 1})
            except Exception:
                logger.exception("Failed processing signal message")
    finally:
        logger.info("Shutting down consumer...")
        await consumer.stop()
        await redis_client.close_pool()
        await mongodb.close_pool()
        await postgres.close_pool()


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Register SIGTERM/SIGINT handlers that set the shutdown event."""
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    _install_signal_handlers(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
