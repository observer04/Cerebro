import time

from fastapi import APIRouter, Request

from app.config import settings
from app.db import kafka as kafka_db
from app.db import mongodb, postgres, redis_client

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Infrastructure health check",
    description=(
        "Probes Kafka, Redis, MongoDB, and PostgreSQL with lightweight checks "
        "(PING, SELECT 1, metadata). Reports `healthy` or `degraded` status, "
        "per-component latencies, real-time throughput, and uptime."
    ),
)
async def health(request: Request) -> dict:
    """Run liveness probes against all backing services and report throughput."""
    components: dict[str, dict] = {}
    degraded = False

    async def record(name: str, status: str, latency_ms: float, extra: dict | None = None):
        payload = {"status": status, "latency_ms": latency_ms}
        if extra:
            payload.update(extra)
        components[name] = payload

    redis = None
    start = time.perf_counter()
    try:
        redis = redis_client.get_client()
        await redis.ping()
        await record("redis", "up", (time.perf_counter() - start) * 1000)
    except Exception as exc:
        degraded = True
        await record("redis", "down", (time.perf_counter() - start) * 1000, {"error": str(exc)})

    start = time.perf_counter()
    try:
        async with postgres.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await record("postgresql", "up", (time.perf_counter() - start) * 1000)
    except Exception as exc:
        degraded = True
        await record("postgresql", "down", (time.perf_counter() - start) * 1000, {"error": str(exc)})

    start = time.perf_counter()
    try:
        db = mongodb.get_db()
        await db.command("ping")
        await record("mongodb", "up", (time.perf_counter() - start) * 1000)
    except Exception as exc:
        degraded = True
        await record("mongodb", "down", (time.perf_counter() - start) * 1000, {"error": str(exc)})

    start = time.perf_counter()
    try:
        producer = kafka_db.get_producer()
        brokers = producer.client.cluster.brokers()
        status = "up" if brokers else "down"
        if not brokers:
            degraded = True
        await record("kafka", status, (time.perf_counter() - start) * 1000, {"lag": 0})
    except Exception as exc:
        degraded = True
        await record("kafka", "down", (time.perf_counter() - start) * 1000, {"error": str(exc), "lag": 0})

    throughput_rate = request.app.state.last_throughput
    if components.get("redis", {}).get("status") == "up" and redis is not None:
        try:
            raw_rate = await redis.get(settings.throughput_rate_key)
            if raw_rate is not None:
                throughput_rate = float(raw_rate)
        except Exception:
            pass

    uptime_seconds = int(time.monotonic() - request.app.state.start_time)

    return {
        "status": "degraded" if degraded else "healthy",
        "components": components,
        "throughput": {
            "signals_per_second": throughput_rate,
            "window_seconds": request.app.state.throughput_window_seconds,
        },
        "uptime_seconds": uptime_seconds,
    }
