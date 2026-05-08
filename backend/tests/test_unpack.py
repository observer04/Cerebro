import asyncio
from typing import Any

async def debounce_and_process() -> tuple[str, str]:
    return ("created", "123")

async def main():
    res = await debounce_and_process()
    print("res is:", repr(res))
    outcome, w_id = res

asyncio.run(main())
