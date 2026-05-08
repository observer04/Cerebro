from __future__ import annotations

import asyncio
import json
import logging

from app.core.backpressure import async_retry
from app.core.debounce import debounce_and_process
from app.db import kafka as kafka_db
from app.db import mongodb, postgres, redis_client
from app.models.signal import SignalIn

logger = logging.getLogger(__name__)


async def _insert_raw_signal(mongo_db, signal: SignalIn) -> None:
    collection = mongo_db["raw_signals"]

    async def operation() -> None:
        await collection.insert_one(signal.model_dump(mode="json"))

    await async_retry(operation)


async def run() -> None:
    await postgres.init_pool()
    await mongodb.init_pool()
    await redis_client.init_pool()

    consumer = kafka_db.create_consumer("signals", "ims-workers")
    try:
        await consumer.start()
    except Exception:
        logger.exception("Kafka consumer failed to start")
        await redis_client.close_pool()
        await mongodb.close_pool()
        await postgres.close_pool()
        return

    redis = redis_client.get_client()
    mongo_db = mongodb.get_db()
    pg_pool = postgres.get_pool()

    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                signal = SignalIn(**payload)
                await _insert_raw_signal(mongo_db, signal)
                outcome = await debounce_and_process(signal, redis, pg_pool, mongo_db)
                event_type = (
                    "incident.created" if outcome == "created" else "incident.updated"
                )
                event = {
                    "type": event_type,
                    "data": {"component_id": signal.component_id},
                }
                await redis.publish("incidents", json.dumps(event))
                await consumer.commit()
            except Exception:
                logger.exception("Failed processing signal message")
    finally:
        await consumer.stop()
        await redis_client.close_pool()
        await mongodb.close_pool()
        await postgres.close_pool()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
