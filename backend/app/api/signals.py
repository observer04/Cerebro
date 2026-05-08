import json

from fastapi import APIRouter, HTTPException, Request, status

from app.api.rate_limit import limiter
from app.config import settings
from app.db import kafka as kafka_db
from app.models.signal import SignalIn

router = APIRouter(prefix="/api/v1", tags=["signals"])


@router.post(
    "/signals",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a failure signal",
    description=(
        "Accepts a failure signal from a monitoring agent, validates it with Pydantic, "
        "and produces it to the Kafka `signals` topic partitioned by `component_id`. "
        "Returns 202 immediately — processing is fully asynchronous.\n\n"
        "**Rate limits:** 10,000 req/s global, 1,000 req/s per source IP (token bucket)."
    ),
    responses={
        429: {"description": "Rate limit exceeded — `Retry-After` header included."},
        503: {"description": "Kafka broker is unreachable — signal was NOT queued."},
    },
)
@limiter.limit(settings.rate_limit_per_ip)
@limiter.limit(settings.rate_limit_global, key_func=lambda request: "global")
async def ingest_signal(request: Request, signal: SignalIn) -> dict:
    """Queue a failure signal to Kafka for async processing by the consumer worker."""
    producer = kafka_db.get_producer()
    payload = signal.model_dump(mode="json")

    try:
        await producer.send_and_wait(
            "signals",
            json.dumps(payload).encode("utf-8"),
            key=signal.component_id.encode("utf-8"),
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable")

    return {"signal_id": str(signal.signal_id), "status": "queued"}
