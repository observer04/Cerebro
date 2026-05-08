import json

from fastapi import APIRouter, HTTPException, Request, status

from app.api.rate_limit import limiter
from app.config import settings
from app.db import kafka as kafka_db
from app.models.signal import SignalIn

router = APIRouter(prefix="/api/v1", tags=["signals"])


@router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.rate_limit_per_ip)
@limiter.limit(settings.rate_limit_global, key_func=lambda _request: "global")
async def ingest_signal(request: Request, signal: SignalIn) -> dict:
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
