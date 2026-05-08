from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


async def init_pool() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)


async def close_pool() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client not initialized")
    return _client.get_default_database()


def get_collection(name: str) -> AsyncIOMotorCollection:
    return get_db()[name]
