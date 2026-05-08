import asyncio
import logging

logger = logging.getLogger(__name__)


async def run() -> None:
    logger.info("Signal consumer placeholder running. Replace in Stage 4.")
    while True:
        await asyncio.sleep(60)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
