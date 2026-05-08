import asyncio
from dataclasses import dataclass
from typing import Iterable

import httpx

API_URL = "http://localhost:8000/api/v1/signals"


@dataclass(frozen=True)
class Burst:
    delay_seconds: float
    component_id: str
    count: int


BURSTS: Iterable[Burst] = (
    Burst(delay_seconds=0, component_id="database", count=50),
    Burst(delay_seconds=2, component_id="api_gateway", count=30),
    Burst(delay_seconds=4, component_id="cache", count=20),
    Burst(delay_seconds=6, component_id="payment_service", count=10),
)


async def send_signal(client: httpx.AsyncClient, component_id: str) -> None:
    payload = {
        "component_id": component_id,
        "source": "seed_failure_event",
        "metadata": {"scenario": "rdbms_outage"},
    }
    response = await client.post(API_URL, json=payload, timeout=10.0)
    response.raise_for_status()


async def send_burst(client: httpx.AsyncClient, burst: Burst) -> None:
    if burst.delay_seconds:
        await asyncio.sleep(burst.delay_seconds)
    tasks = [send_signal(client, burst.component_id) for _ in range(burst.count)]
    await asyncio.gather(*tasks)
    print(f"Sent {burst.count} signals for {burst.component_id}")


async def main() -> None:
    async with httpx.AsyncClient() as client:
        for burst in BURSTS:
            await send_burst(client, burst)

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
